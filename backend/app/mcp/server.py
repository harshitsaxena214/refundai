"""
RefundGuard MCP Server.

Exposes tools the TrueForge agent can call via the MCP protocol.
Mounted on the FastAPI app at /mcp (HTTP transport).

Tools:
  READ-ONLY:
    get_customer(customer_id)
    get_order(order_id)
    get_payment(order_id)
    get_refund_history(order_id)
    get_refund_policy()
    get_refund_request(refund_request_id)

  CALCULATION:
    calculate_refund(order_id, reason)   — calls policy engine

  MUTATING (requires human approval enforced by TrueForge harness):
    process_refund(refund_request_id, approved_amount)
    create_audit_log(refund_request_id, action, actor, details)
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from app.db.database import SessionLocal
from app.db import models
from app.services import policy_service, audit_service

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="refundguard-api",
    instructions="RefundGuard application tools for refund investigation and processing.",
)


# ── Helper ────────────────────────────────────────────────────────────────

def _get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


# ── READ-ONLY TOOLS ───────────────────────────────────────────────────────

@mcp.tool()
def get_customer(customer_id: str) -> Dict[str, Any]:
    """
    Retrieve customer information by customer ID.

    Args:
        customer_id: Customer ID (e.g. CUST-1001)

    Returns:
        Customer details including name, email, and account creation date.
    """
    db = _get_db()
    try:
        customer = db.get(models.Customer, customer_id)
        if not customer:
            return {"error": f"Customer {customer_id} not found"}
        return {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
        }
    finally:
        db.close()


@mcp.tool()
def get_order(order_id: str) -> Dict[str, Any]:
    """
    Retrieve order details by order ID.

    Args:
        order_id: Order ID (e.g. ORD-1042)

    Returns:
        Order details including product, amount, date, and status.
    """
    db = _get_db()
    try:
        order = db.get(models.Order, order_id)
        if not order:
            return {"error": f"Order {order_id} not found"}
        return {
            "id": order.id,
            "customer_id": order.customer_id,
            "product_name": order.product_name,
            "amount": str(order.amount),
            "currency": order.currency,
            "order_date": order.order_date.isoformat(),
            "status": order.status,
        }
    finally:
        db.close()


@mcp.tool()
def get_payment(order_id: str) -> Dict[str, Any]:
    """
    Retrieve payment information for an order.

    Args:
        order_id: Order ID (e.g. ORD-1042)

    Returns:
        Payment status, amount, method, and date.
    """
    db = _get_db()
    try:
        payment = db.query(models.Payment).filter(
            models.Payment.order_id == order_id
        ).first()
        if not payment:
            return {"error": f"No payment found for order {order_id}"}
        return {
            "id": payment.id,
            "order_id": payment.order_id,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
            "payment_method": payment.payment_method,
            "payment_date": payment.payment_date.isoformat(),
        }
    finally:
        db.close()


@mcp.tool()
def get_refund_history(order_id: str) -> Dict[str, Any]:
    """
    Retrieve refund history for an order.

    Args:
        order_id: Order ID (e.g. ORD-1042)

    Returns:
        List of previous refunds and total amount refunded.
    """
    db = _get_db()
    try:
        # Find all completed refunds for this order
        refunds = db.query(models.Refund).filter(
            models.Refund.order_id == order_id,
            models.Refund.status == "COMPLETED",
        ).all()

        refund_list = [
            {
                "id": r.id,
                "amount": str(r.amount),
                "currency": r.currency,
                "status": r.status,
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            }
            for r in refunds
        ]
        total = sum(r.amount for r in refunds)

        return {
            "order_id": order_id,
            "previous_refunds": refund_list,
            "total_refunded": str(total),
            "count": len(refund_list),
        }
    finally:
        db.close()


@mcp.tool()
def get_refund_policy() -> Dict[str, Any]:
    """
    Retrieve the authoritative refund policy document.

    Use this to understand what refund percentages apply under what conditions.
    Never invent or assume policy rules — always retrieve them with this tool.

    Returns:
        The complete refund policy with all rules and conditions.
    """
    return policy_service.get_policy_document()


@mcp.tool()
def get_refund_request(refund_request_id: str) -> Dict[str, Any]:
    """
    Retrieve a refund request by ID.

    Args:
        refund_request_id: Refund request ID (e.g. RR-001)

    Returns:
        Refund request details including order_id, reason, and requested amount.
    """
    db = _get_db()
    try:
        rr = db.get(models.RefundRequest, refund_request_id)
        if not rr:
            return {"error": f"Refund request {refund_request_id} not found"}
        return {
            "id": rr.id,
            "order_id": rr.order_id,
            "reason": rr.reason,
            "requested_amount": str(rr.requested_amount),
            "status": rr.status,
        }
    finally:
        db.close()


# ── CALCULATION TOOL ──────────────────────────────────────────────────────

@mcp.tool()
def calculate_refund(order_id: str, reason: str) -> Dict[str, Any]:
    """
    Calculate the recommended refund amount using the refund policy engine.

    This tool runs the deterministic policy calculation and returns a full
    audit trail of the computation. The agent must use this tool rather than
    performing calculations itself.

    Args:
        order_id: Order ID to calculate refund for
        reason: Customer's stated reason for the refund

    Returns:
        Calculation result including eligibility, recommended amount, policy rule,
        risk level, risk score, and step-by-step calculation trace.
    """
    db = _get_db()
    try:
        order = db.get(models.Order, order_id)
        if not order:
            return {"error": f"Order {order_id} not found"}

        # Find any existing refund request for context
        rr = db.query(models.RefundRequest).filter(
            models.RefundRequest.order_id == order_id
        ).order_by(models.RefundRequest.created_at.desc()).first()
        requested_amount = Decimal(str(rr.requested_amount)) if rr else Decimal(str(order.amount))

        # Previous refunds
        refunds = db.query(models.Refund).filter(
            models.Refund.order_id == order_id,
            models.Refund.status == "COMPLETED",
        ).all()
        previous_total = sum(r.amount for r in refunds)

        # Age of order
        order_age_days = (date.today() - order.order_date).days

        # Run policy engine
        result = policy_service.evaluate_refund(
            order_age_days=order_age_days,
            reason=reason,
            order_amount=Decimal(str(order.amount)),
            requested_amount=requested_amount,
            previous_refund_total=Decimal(str(previous_total)),
        )

        # Write audit log
        audit_service.log(
            db,
            action=audit_service.Actions.REFUND_CALCULATED,
            refund_request_id=rr.id if rr else None,
            actor="agent",
            details={
                "order_id": order_id,
                "policy_rule": result.policy_rule_id,
                "recommended_amount": str(result.recommended_amount),
                "risk_level": result.risk_level,
            },
        )

        return {
            "order_id": order_id,
            "order_amount": str(order.amount),
            "order_age_days": order_age_days,
            "reason_provided": reason,
            "eligible": result.eligible,
            "refund_percentage": result.refund_percentage,
            "recommended_amount": str(result.recommended_amount),
            "policy_rule_id": result.policy_rule_id,
            "policy_rule_description": result.policy_rule_description,
            "risk_level": result.risk_level,
            "risk_score": result.risk_score,
            "reject_reason": result.reject_reason,
            "calculation_steps": result.calculation_steps,
        }
    finally:
        db.close()


# ── MUTATING TOOLS (process_refund requires TrueForge human approval) ─────

@mcp.tool()
def process_refund(refund_request_id: str, approved_amount: float) -> Dict[str, Any]:
    """
    Execute a refund after human approval.

    IMPORTANT: This tool REQUIRES explicit human approval from the TrueForge
    approval gate before it can be called. The system enforces this at multiple
    levels:
      1. TrueForge harness pauses before this tool and waits for human input
      2. This function independently verifies approval status in the database
      3. This function verifies the amount does not exceed the order amount
      4. This function checks for duplicate refunds

    Args:
        refund_request_id: The refund request to process
        approved_amount: The amount to refund (must be <= order amount)

    Returns:
        Refund result with transaction ID and status.
    """
    db = _get_db()
    try:
        # ── Safety Check 1: Refund request must exist ──────────────────────
        rr = db.get(models.RefundRequest, refund_request_id)
        if not rr:
            return {"error": f"Refund request {refund_request_id} not found", "blocked": True}

        # ── Safety Check 2: Must be APPROVED status ────────────────────────
        # This is the critical server-side enforcement.
        # Even if the LLM somehow bypassed TrueForge's approval gate,
        # this check ensures no refund is processed without human sign-off.
        if rr.status != "APPROVED":
            logger.warning(
                "process_refund called with status=%s for RR=%s — BLOCKED",
                rr.status, refund_request_id
            )
            return {
                "error": (
                    f"Refund request {refund_request_id} has status '{rr.status}'. "
                    "Human approval is required before processing."
                ),
                "blocked": True,
                "current_status": rr.status,
            }

        # ── Safety Check 3: Order must exist and payment must be completed ─
        order = db.get(models.Order, rr.order_id)
        if not order:
            return {"error": f"Order {rr.order_id} not found", "blocked": True}

        payment = db.query(models.Payment).filter(
            models.Payment.order_id == rr.order_id
        ).first()
        if not payment or payment.status != "COMPLETED":
            return {
                "error": "Payment not completed for this order",
                "blocked": True,
                "payment_status": payment.status if payment else "NOT_FOUND",
            }

        # ── Safety Check 4: Amount must be a valid positive numeric value ──
        order_amount = Decimal(str(order.amount))
        try:
            refund_amount = Decimal(str(approved_amount)).quantize(Decimal("0.01"))
        except Exception:
            return {
                "error": f"Invalid refund amount: '{approved_amount}' is not a valid numeric value.",
                "blocked": True,
            }

        if refund_amount <= Decimal("0.00"):
            return {
                "error": f"Refund amount must be greater than 0. Got: ${refund_amount}",
                "blocked": True,
            }

        if refund_amount > order_amount:
            return {
                "error": f"Approved amount ${refund_amount} exceeds order amount ${order_amount}",
                "blocked": True,
            }

        # ── Safety Check 5: Check for duplicate refund ────────────────────
        existing_refunds = db.query(models.Refund).filter(
            models.Refund.order_id == rr.order_id,
            models.Refund.status == "COMPLETED",
        ).all()
        total_already_refunded = sum(r.amount for r in existing_refunds)
        if total_already_refunded + refund_amount > order_amount:
            return {
                "error": (
                    f"Total refunds (${total_already_refunded} existing + ${refund_amount} new) "
                    f"would exceed order amount ${order_amount}"
                ),
                "blocked": True,
            }

        # ── All checks passed — execute refund ────────────────────────────
        from datetime import datetime

        # Generate refund ID
        refund_count = db.query(models.Refund).count()
        refund_id = f"REF-{refund_count + 1:04d}"

        refund = models.Refund(
            id=refund_id,
            refund_request_id=refund_request_id,
            order_id=rr.order_id,
            amount=refund_amount,
            currency=order.currency,
            status="COMPLETED",
            processed_at=datetime.utcnow(),
        )
        db.add(refund)

        # Update refund request status to COMPLETED
        rr.status = "COMPLETED"
        rr.updated_at = datetime.utcnow()
        db.commit()

        # Write audit log
        audit_service.log(
            db,
            action=audit_service.Actions.REFUND_PROCESSED,
            refund_request_id=refund_request_id,
            actor="agent",
            details={
                "refund_id": refund_id,
                "amount": str(refund_amount),
                "currency": order.currency,
                "order_id": rr.order_id,
            },
        )
        audit_service.log(
            db,
            action=audit_service.Actions.AUDIT_COMPLETED,
            refund_request_id=refund_request_id,
            actor="system",
        )

        logger.info(
            "Refund processed: %s for RR=%s amount=$%s",
            refund_id, refund_request_id, refund_amount
        )
        return {
            "success": True,
            "refund_id": refund_id,
            "refund_request_id": refund_request_id,
            "order_id": rr.order_id,
            "amount": str(refund_amount),
            "currency": order.currency,
            "status": "COMPLETED",
            "message": f"Refund of ${refund_amount} processed successfully.",
        }

    except Exception as e:
        logger.exception("Error processing refund %s", refund_request_id)
        db.rollback()
        return {"error": str(e), "blocked": False}
    finally:
        db.close()


@mcp.tool()
def create_audit_log(
    refund_request_id: str,
    action: str,
    actor: str = "agent",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create an audit log entry for an important action.

    Args:
        refund_request_id: Associated refund request ID
        action: Action name (e.g. CUSTOMER_RETRIEVED, ORDER_VERIFIED)
        actor: Who performed the action (agent / human / system)
        details: Optional additional details as key-value pairs

    Returns:
        Created audit log entry ID and timestamp.
    """
    db = _get_db()
    try:
        entry = audit_service.log(
            db,
            action=action,
            refund_request_id=refund_request_id,
            actor=actor,
            details=details or {},
        )
        return {
            "id": entry.id,
            "action": entry.action,
            "actor": entry.actor,
            "created_at": entry.created_at.isoformat(),
        }
    finally:
        db.close()
