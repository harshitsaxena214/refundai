# 🛡️ RefundGuard

### AI-powered refund investigation with human-controlled execution.

**RefundGuard** is an AI agent system that automates the investigation of customer refund requests while keeping the final refund decision and execution under human control.

Instead of forcing a support agent to manually search through customer records, orders, payments, refund history, and policies, RefundGuard uses an AI agent to gather context, analyze the case, determine eligibility, calculate the refund amount, and present a recommendation.

> **AI investigates → AI recommends → Human authorizes → System executes**

---

## 🎯 The Problem

Customer-support teams receive a large number of refund requests.

A typical refund investigation requires an employee to manually:

* Find the customer
* Find the order
* Verify payment status
* Check previous refunds
* Retrieve the refund policy
* Determine whether the request is valid
* Calculate the refund amount
* Process the refund
* Record the activity

This process is repetitive, slow, and susceptible to human error.

Giving an AI agent unrestricted access to refund operations creates another problem:

> **What happens if the AI makes a mistake and executes an irreversible operation?**

RefundGuard solves both problems by separating **investigation** from **authorization**.

---

# 💡 The Solution

RefundGuard places an AI investigation agent between the support employee and the refund system.

```text
Support Agent
      │
      │ "Refund ORD-1042 because the product was damaged"
      ▼
┌──────────────────────────┐
│     RefundGuard Agent    │
└────────────┬─────────────┘
             │
             ├── Get customer
             ├── Get order
             ├── Verify payment
             ├── Check refund history
             ├── Get refund policy
             └── Calculate refund
                     │
                     ▼
              Analyze the case
                     │
                     ▼
              AI Recommendation
                     │
                     ▼
            ⚠️ HUMAN APPROVAL
                 /        \
              Reject      Approve
                │            │
                ▼            ▼
               Stop      Process Refund
                              │
                              ▼
                          Audit Log
```

The AI can investigate and recommend.

It **cannot authorize the final refund**.

---

# 🧠 Example

A customer submits:

> "My $149 headphones arrived damaged. I want a refund."

RefundGuard gathers the relevant information:

```text
Customer:           Alice Johnson
Order:              ORD-1042
Amount:             $149
Order age:          7 days
Payment:            Completed
Previous refunds:   None
Reason:             Damaged product
```

The agent retrieves the applicable policy:

```text
Damaged product
      ↓
Within 30 days
      ↓
100% refund
```

The AI produces:

```text
┌─────────────────────────────────────┐
│             ELIGIBLE                │
│                                     │
│ Recommended refund: $149            │
│ Risk: LOW                           │
│                                     │
│ The order is 7 days old and the     │
│ damaged-product policy allows a     │
│ 100% refund within 30 days.         │
└─────────────────────────────────────┘
```

But RefundGuard does **not** immediately process the refund.

Instead:

```text
⚠️ HUMAN APPROVAL REQUIRED

Refund $149?

[ REJECT ]        [ APPROVE REFUND ]
```

Only after the support employee approves the request can the refund operation execute.

---

# 🔐 Safety Architecture

The most important design principle in RefundGuard is that **the safety boundary is enforced by the backend**, not just by an AI instruction.

The system follows:

```text
AI investigates
       ↓
AI recommends
       ↓
Human authorizes
       ↓
Backend verifies authorization
       ↓
System executes
       ↓
Audit log
```

If the AI attempts to execute a refund without approval:

```text
AI
 │
 ▼
process_refund()
 │
 ▼
Authorization Check
 │
 ├── No approval ──→ 403 Forbidden
 │
 └── Approved ────→ Execute refund
```

This means the agent cannot bypass the approval layer simply by calling the refund tool.

---

# 🔄 End-to-End Workflow

```text
1. Customer submits refund request
              ↓
2. Support agent creates investigation
              ↓
3. RefundGuard AI agent starts investigation
              ↓
4. Retrieve customer information
              ↓
5. Retrieve order information
              ↓
6. Verify payment
              ↓
7. Check refund history
              ↓
8. Retrieve refund policy
              ↓
9. Analyze eligibility
              ↓
10. Calculate refund amount
              ↓
11. Generate recommendation
              ↓
12. Human reviews recommendation
              ↓
       ┌──────┴──────┐
       ▼             ▼
    Reject         Approve
       │             │
       ▼             ▼
      Stop      Authorization
                     │
                     ▼
               Process refund
                     │
                     ▼
                 Audit log
```

---

# 🔧 TrueForge

RefundGuard uses **TrueForge** as the agent execution and orchestration layer.

TrueForge is an open-source agent harness that handles the runtime layer required to turn an LLM into a working agent, including model calls, MCP tools, sandboxing, approvals, context management, and session state. It exposes a chat UI, HTTP API/SDK, and embeddable UI SDK.

In RefundGuard, TrueForge orchestrates the investigation workflow:

```text
                    TrueForge
                       │
                       ▼
                  AI Agent
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    get_customer   get_order   get_payment
          │            │            │
          └────────────┼────────────┘
                       ▼
              get_refund_history
                       │
                       ▼
               get_refund_policy
                       │
                       ▼
                Analyze case
                       │
                       ▼
              Calculate refund
                       │
                       ▼
             AI Recommendation
                       │
                       ▼
              HUMAN APPROVAL
                       │
                       ▼
               process_refund
                       │
                       ▼
                  Audit Log
```

### MCP Tools

The RefundGuard agent can work with structured tools such as:

```text
get_customer()
get_order()
get_payment()
get_refund_history()
get_refund_policy()
calculate_refund()
process_refund()
```

The `process_refund()` operation is protected by the application's authorization layer.

TrueForge supports remote MCP servers, sandbox execution, human checkpoints and tool approvals, making it well suited for this type of controlled agent workflow.

### Why TrueForge?

RefundGuard needs more than an LLM response.

It needs:

* Agent execution
* Tool calling
* MCP integration
* Human checkpoints
* Sandbox execution
* Context management
* Session state
* Streaming
* Approval workflows

TrueForge provides these agent-runtime capabilities as an open-source harness.

---

# 🧪 Sandbox

RefundGuard uses a sandbox environment for demonstrating refund execution safely.

The sandbox allows the project to demonstrate the complete workflow without connecting the hackathon demo to real payment infrastructure.

```text
AI Recommendation
       ↓
Human Approval
       ↓
Sandbox
       ↓
Simulated Refund
       ↓
Audit Log
```

TrueForge supports sandbox-as-a-tool and currently lists Daytona as a sandbox provider.

---

# 🔍 Qodo

**Qodo** was used as part of the development and code-quality workflow for RefundGuard.

Qodo provides AI-powered, context-aware code review and engineering-quality tooling across IDEs, pull requests, CLI and Git workflows. Its platform can surface bugs, requirements gaps, rule violations and other issues using broader codebase context.

For RefundGuard, Qodo helped support the development process by providing an additional quality layer around the application code.

```text
                RefundGuard
                     │
                     ▼
              Development
                     │
                     ▼
                   Qodo
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
      Code Review  Issues     Rules
          │          │          │
          └──────────┼──────────┘
                     ▼
              Improved Code
```

Qodo's current platform includes context-aware review, agentic issue finding, rule enforcement, codebase intelligence, and governance capabilities.

### Why Qodo?

AI-generated code can move quickly, but speed without review can introduce bugs and regressions.

Qodo provides an additional engineering-quality layer that helps:

* Identify potential bugs
* Review AI-generated code
* Detect logic gaps
* Enforce engineering standards
* Understand changes using codebase context
* Improve code-review workflows

Qodo also provides reusable Agent Skills that can apply engineering rules and surface issues earlier in the development workflow.

---

## Qodo Code Review Evidence

Qodo reviewed a representative hackathon change focused on adding
server-side validation around refund amounts in RefundGuard.
The review checked the implementation for bugs, rule violations,
and requirement gaps, and Qodo reported no material issues requiring changes.

### Representative Pull Request

[PR #2 - Add refund amount validation](https://github.com/harshitsaxena214/refundai/pull/2)

This pull request contains a meaningful hackathon change to the
refund execution flow and was reviewed by Qodo before being merged.

### Qodo Review Result

Qodo's review reported:

- **Bugs:** 0
- **Rule violations:** 0
- **Requirement gaps:** 0
- **Result:** No material issues found

![Qodo Code Review] 
<img width="1366" height="716" alt="Screenshot 2026-08-30 004649" src="https://github.com/user-attachments/assets/c8530438-2861-463f-a696-97b1c34f052f" />


### Review History

1. Created a feature branch for the refund amount validation change.
2. Opened a GitHub pull request containing the implementation.
3. Qodo reviewed the pull request.
4. Qodo reported no material issues requiring changes.
5. No code changes were required following the review.
6. The pull request was merged after review.

---

# 🏗️ Architecture

```text
┌─────────────────────────────────────────────┐
│                  FRONTEND                   │
│                                             │
│  Landing Page │ Dashboard │ Investigation   │
└──────────────────────┬──────────────────────┘
                       │
                       │ API
                       ▼
┌─────────────────────────────────────────────┐
│                  BACKEND                    │
│                                             │
│ Customers │ Orders │ Payments │ Refunds    │
│ Policies  │ Approvals │ Audit Logs          │
└──────────────────────┬──────────────────────┘
                       │
                       │ MCP / Agent API
                       ▼
┌─────────────────────────────────────────────┐
│                 TRUEFORGE                   │
│                                             │
│ Agent Runtime                               │
│ MCP Tools                                   │
│ Human Approval                              │
│ Context Management                          │
│ Sandbox                                     │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
              RefundGuard Tools
                       │
           ┌───────────┼───────────┐
           ▼           ▼           ▼
       Customer      Orders      Payments
                                   │
                                   ▼
                              Refund System
                                   │
                                   ▼
                              Audit Logs
```

---

# 🖥️ Application

## Landing Page

The landing page explains the core idea behind RefundGuard:

```text
Problem
   ↓
AI Investigation
   ↓
Policy Analysis
   ↓
Human Approval
   ↓
Safe Execution
   ↓
Auditability
```

The visual design uses a premium dark interface with restrained amber accents to communicate trust, security and controlled automation.

---

## Dashboard

The dashboard provides an overview of refund investigations.

Example statuses:

```text
Pending
Investigating
Awaiting Approval
Approved
Rejected
Completed
```

---

## Investigation

The investigation page provides the complete context behind a refund decision.

It includes:

* Customer information
* Order details
* Payment status
* Refund history
* Refund policy
* AI recommendation
* Risk assessment
* Recommended refund amount
* Human approval controls
* Execution status
* Activity timeline
* Audit information

---

# 📋 Auditability

Every important stage of the workflow can be represented in the activity timeline:

```text
✓ Investigation created

✓ Customer information retrieved

✓ Order information retrieved

✓ Payment verified

✓ Refund history checked

✓ Refund policy evaluated

✓ AI recommendation generated

⚠ Awaiting human approval

✓ Refund approved

✓ Refund processed

✓ Audit record created
```

This provides visibility into how the final decision was reached.

---

# 🛡️ Core Safety Principle

RefundGuard intentionally separates **intelligence** from **authority**.

| Capability            |  AI | Human | Backend |
| --------------------- | :-: | :---: | :-----: |
| Investigate request   |  ✓  |       |         |
| Retrieve customer     |  ✓  |       |         |
| Retrieve order        |  ✓  |       |         |
| Check payment         |  ✓  |       |         |
| Check refund history  |  ✓  |       |         |
| Evaluate policy       |  ✓  |       |         |
| Calculate refund      |  ✓  |       |         |
| Recommend refund      |  ✓  |       |         |
| Approve refund        |     |   ✓   |         |
| Enforce authorization |     |       |    ✓    |
| Execute refund        |     |       |    ✓    |
| Record audit event    |     |       |    ✓    |

The AI can make a recommendation.

**It does not get the final authority.**

---

# 🚀 Hackathon Demo

RefundGuard is designed to communicate the complete concept in a short demonstration.

### Demo flow

```text
1. Open RefundGuard
        ↓
2. Create a refund investigation
        ↓
3. Enter:
   "My $149 headphones arrived damaged"
        ↓
4. AI investigates the request
        ↓
5. Agent retrieves customer/order/payment data
        ↓
6. Agent checks refund policy
        ↓
7. AI determines:
   Eligible — $149 — Low Risk
        ↓
8. Human Approval Required
        ↓
9. Click "Approve Refund"
        ↓
10. Backend authorizes operation
        ↓
11. Sandbox executes simulated refund
        ↓
12. Audit timeline records the operation
```

### The key moment

```text
AI recommends:

        REFUND $149
        RISK: LOW

              ↓

      HUMAN APPROVAL

              ↓

          APPROVE

              ↓

      REFUND EXECUTED
```

This demonstrates the project's central idea:

> **AI can perform complex business investigations without being given unrestricted authority over irreversible actions.**

---

# 🌎 Potential Applications

The same architecture can be extended beyond refunds.

### Payments

```text
AI investigates payment issue
        ↓
Human approval
        ↓
Payment operation
```

### Account changes

```text
AI verifies identity and request
        ↓
Human approval
        ↓
Account modification
```

### Insurance claims

```text
AI investigates claim
        ↓
AI evaluates policy
        ↓
Human approval
        ↓
Claim processing
```

### Order cancellations

```text
AI checks order status
        ↓
AI determines eligibility
        ↓
Human approval
        ↓
Cancellation
```

### Financial operations

```text
AI analyzes transaction
        ↓
Risk assessment
        ↓
Human authorization
        ↓
Execution
```

---

# 🧰 Technology

RefundGuard brings together:

* **AI Agent** — investigates and reasons about refund requests
* **TrueForge** — agent execution, MCP tools, sandboxing and human checkpoints
* **MCP** — structured access to application capabilities
* **Backend API** — business logic and authorization
* **Database** — customer, order, refund and audit data
* **Sandbox** — safe simulated refund execution
* **Qodo** — AI-assisted code review, contextual quality checks and engineering workflow support
* **Frontend** — support dashboard, investigation workflow and approval interface

---

# 🧠 What Makes RefundGuard Different?

The goal isn't simply:

> "Use AI to process refunds."

The goal is:

> **"Use AI to safely investigate and automate a real business operation while keeping humans in control of irreversible actions."**

RefundGuard demonstrates a practical pattern for deploying AI agents in environments where **accuracy, authorization, traceability and safety** matter.

---

# 🏆 Built for the Hackathon

RefundGuard combines:

```text
AI Agent
   +
MCP Tool Calling
   +
TrueForge
   +
Sandbox Execution
   +
Human-in-the-Loop
   +
Authorization
   +
Audit Logs
   +
Frontend
   +
Backend
   +
AI-assisted Development
```

The result is a simple, understandable demonstration of **safe agentic automation for real-world business workflows**.

---

## 🔗 Credits & Technologies

### TrueForge

Open-source agent harness by TrueFoundry.

[TrueForge GitHub](https://github.com/truefoundry/trueforge?utm_source=chatgpt.com)

### Qodo

AI-powered code review and code-quality platform.

[Qodo](https://www.qodo.ai/?utm_source=chatgpt.com)

---

<div align="center">

### RefundGuard

**AI investigates. Humans authorize. Systems execute safely.**

</div>
