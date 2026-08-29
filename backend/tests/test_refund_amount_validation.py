"""
Tests for server-side refund amount validation in process_refund().

These tests verify that invalid amounts are rejected before refund execution,
regardless of who calls the MCP tool (agent or direct caller).

Tested cases:
  - Valid refund amount (approved flow still works)
  - Amount of 0   → blocked
  - Negative amount → blocked
  - Amount > order amount → blocked
  - Amount > remaining refundable amount → blocked
  - Invalid (non-numeric) value → blocked
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, call
from datetime import date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_db(
    rr_status: str = "APPROVED",
    order_amount: Decimal = Decimal("100.00"),
    payment_status: str = "COMPLETED",
    previous_refunds_total: Decimal = Decimal("0.00"),
):
    """
    Build a minimal mock DB that passes Safety Checks 1-3 so that we can
    focus tests on Safety Check 4 (amount validation) and Check 5
    (remaining refundable amount).
    """
    mock_rr = MagicMock()
    mock_rr.status = rr_status
    mock_rr.order_id = "ORD-TEST"

    mock_order = MagicMock()
    mock_order.id = "ORD-TEST"
    mock_order.amount = order_amount
    mock_order.currency = "USD"

    mock_payment = MagicMock()
    mock_payment.status = payment_status

    # Build existing refund records to simulate previous refunds
    mock_existing_refunds = []
    if previous_refunds_total > 0:
        mock_ref = MagicMock()
        mock_ref.amount = previous_refunds_total
        mock_existing_refunds.append(mock_ref)

    mock_db = MagicMock()
    mock_db.get.side_effect = lambda model, key: {
        "RR-TEST": mock_rr,
        "ORD-TEST": mock_order,
    }.get(key)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_payment
    mock_db.query.return_value.filter.return_value.all.return_value = mock_existing_refunds
    mock_db.query.return_value.count.return_value = 0

    return mock_db


# ---------------------------------------------------------------------------
# Import the raw function under test (bypassing MCP decorator registration)
# ---------------------------------------------------------------------------

def _call_process_refund(refund_request_id, approved_amount, mock_db):
    """
    Call the process_refund logic directly, patching _get_db.
    audit_service.log is also patched to avoid DB writes.
    """
    with patch("app.mcp.server._get_db", return_value=mock_db), \
         patch("app.mcp.server.audit_service") as _mock_audit:
        from app.mcp.server import process_refund
        return process_refund(refund_request_id, approved_amount)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRefundAmountValidation:

    def test_valid_amount_passes(self):
        """Valid approved amount within order total must succeed."""
        mock_db = _make_mock_db(order_amount=Decimal("100.00"))
        result = _call_process_refund("RR-TEST", 50.00, mock_db)
        assert result.get("blocked") is not True
        assert result.get("success") is True

    def test_zero_amount_blocked(self):
        """Amount of exactly 0 must be rejected."""
        mock_db = _make_mock_db(order_amount=Decimal("100.00"))
        result = _call_process_refund("RR-TEST", 0.00, mock_db)
        assert result.get("blocked") is True
        assert "greater than 0" in result["error"].lower() or "0" in result["error"]

    def test_negative_amount_blocked(self):
        """Negative amounts must be rejected."""
        mock_db = _make_mock_db(order_amount=Decimal("100.00"))
        result = _call_process_refund("RR-TEST", -25.00, mock_db)
        assert result.get("blocked") is True
        assert "greater than 0" in result["error"].lower() or "0" in result["error"]

    def test_amount_exceeds_order_amount_blocked(self):
        """Amount greater than the original order amount must be rejected."""
        mock_db = _make_mock_db(order_amount=Decimal("100.00"))
        result = _call_process_refund("RR-TEST", 150.00, mock_db)
        assert result.get("blocked") is True
        assert "exceed" in result["error"].lower() or "order amount" in result["error"].lower()

    def test_amount_exceeds_remaining_refundable_blocked(self):
        """
        Amount that, combined with previous refunds, exceeds the order total
        must be rejected even if it is individually less than the order amount.
        """
        # Order is $100, $60 already refunded → only $40 remaining
        mock_db = _make_mock_db(
            order_amount=Decimal("100.00"),
            previous_refunds_total=Decimal("60.00"),
        )
        result = _call_process_refund("RR-TEST", 50.00, mock_db)  # $60 + $50 = $110 > $100
        assert result.get("blocked") is True
        assert "exceed" in result["error"].lower() or "order amount" in result["error"].lower()

    def test_invalid_non_numeric_blocked(self):
        """
        A non-numeric value for approved_amount must return a clean blocked error.
        (Guards against crafted MCP inputs.)
        """
        mock_db = _make_mock_db(order_amount=Decimal("100.00"))
        result = _call_process_refund("RR-TEST", "not-a-number", mock_db)
        assert result.get("blocked") is True
        assert "valid" in result["error"].lower() or "numeric" in result["error"].lower() or "invalid" in result["error"].lower()

    def test_approved_flow_still_passes(self):
        """
        Full happy path: APPROVED status + valid amount must complete successfully.
        Ensures the existing approval flow is not broken.
        """
        mock_db = _make_mock_db(
            rr_status="APPROVED",
            order_amount=Decimal("200.00"),
            payment_status="COMPLETED",
            previous_refunds_total=Decimal("0.00"),
        )
        result = _call_process_refund("RR-TEST", 100.00, mock_db)
        assert result.get("success") is True
        assert result.get("blocked") is not True
        assert result["amount"] == "100.00"
