# Veridian Internal IT Service Agent

> **Policy-Grounded Agentic AI for Internal IT Support**
> Understand → Retrieve → Assess → Decide → Act → Audit

A production-oriented prototype of an **Internal Employee IT Support Agent** built for the **AIONOS Agentic AI Factory — Round 1, Assignment 2**.

The system transforms unstructured employee IT requests into **policy-grounded, traceable decisions**:

* **RESOLVE** simple, low-risk requests
* **CLARIFY** when required information is missing or the request is ambiguous
* **ESCALATE** risky, security-sensitive, or cross-functional requests
* Create structured tickets when required
* Surface the policy evidence behind decisions
* Use historical tickets as contextual precedent
* Maintain an append-only audit trail

The goal is not to build another generic chatbot.

The goal is to demonstrate how an **agentic service workflow can make controlled, explainable and auditable decisions from enterprise knowledge.**

---

## Demo

### Core workflow

```text
                    Employee Request
                           │
                           ▼
                  ┌──────────────────┐
                  │   Intent Router  │
                  └────────┬─────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │   Policy Search Engine  │
              │   + Historical Context  │
              └────────────┬────────────┘
                           │
                           ▼
                ┌────────────────────┐
                │ Risk & Decision    │
                │      Engine        │
                └─────────┬──────────┘
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
          RESOLVE      CLARIFY      ESCALATE
             │            │            │
             └────────────┼────────────┘
                          ▼
                 ┌─────────────────┐
                 │ Action / Ticket │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │   Audit Trail   │
                 └─────────────────┘
```

---

# Why this project?

Internal IT support requests are often deceptively simple.

Examples:

> "My VPN stopped working."

> "Can you install this software?"

> "I need admin access urgently."

> "My laptop is dead."

> "It isn't working."

A useful enterprise support agent must do more than generate a conversational response.

It needs to determine:

1. What is the employee actually asking for?
2. Which organizational policy applies?
3. Is enough information available?
4. Is the request safe to resolve automatically?
5. Does another department need to approve or process it?
6. Should an IT ticket be created?
7. What evidence supports the decision?
8. What happened during the interaction?

This project addresses that workflow through a **policy-grounded agentic architecture**.

---

# Key Capabilities

| Capability               | Implementation                           |
| ------------------------ | ---------------------------------------- |
| Intent classification    | Deterministic issue router               |
| Policy grounding         | TF-IDF / cosine-similarity retrieval     |
| Multi-turn clarification | Stateful conversation handling           |
| Risk assessment          | Rule-based risk engine                   |
| Decision making          | RESOLVE / CLARIFY / ESCALATE             |
| Ticketing                | Structured JSON ticket store             |
| Historical context       | Existing ticket queue                    |
| Auditability             | Append-only JSONL audit trail            |
| UI                       | Streamlit operations console             |
| Batch validation         | Official request QA workflow             |
| Testing                  | Pytest behavioral tests                  |
| Deployment               | Streamlit-ready local/cloud architecture |

---

# Agentic Workflow

The system follows a controlled tool-oriented workflow:

```text
OBSERVE
   ↓
CLASSIFY
   ↓
RETRIEVE
   ↓
ASSESS
   ↓
CHECK INFORMATION
   ↓
DECIDE
   ↓
ACT
   ↓
AUDIT
```

### 1. Observe

The agent receives an employee request together with available employee/context information.

### 2. Classify

The request is routed into an IT issue category such as:

* Password Reset
* VPN
* Software Access
* Hardware
* Printer
* Email
* Security Incident
* Work-From-Home Equipment
* Expense Software Access
* Unknown / Ambiguous

### 3. Retrieve

The system searches the official Veridian IT knowledge base for relevant policy evidence.

Historical tickets may also be retrieved as **contextual precedent**, but they are never treated as policy.

### 4. Assess

The agent determines:

* risk level
* required information
* applicable policy
* whether another department is involved
* whether automatic resolution is appropriate

### 5. Decide

Every request reaches one of three controlled outcomes:

```text
RESOLVE
CLARIFY
ESCALATE
```

### 6. Act

Depending on the decision, the system can:

* provide policy-backed guidance
* request missing information
* create a structured ticket
* record an escalation
* record an audit event

### 7. Audit

Meaningful actions are recorded in an append-only JSONL audit trail.

This creates an inspectable history of how the system reached and executed its decision.

---

# Policy Grounding

The agent operates against the official **Veridian Corp Data Pack** supplied for the assignment.

The knowledge base contains:

```text
KB-01  Password Reset
KB-02  VPN Access
KB-03  Laptop Replacement
KB-04  Software Installation
KB-05  Printer
KB-06  Email
KB-07  Guest Wi-Fi
KB-08  Expense Software Access
KB-09  Security Incident Reporting
KB-10  Work-From-Home Equipment

Asset Management Policy
```

The application is designed to avoid inventing organizational rules.

When sufficient policy evidence cannot be established, the system prefers **clarification or escalation** over unsupported claims.

---

# Decision Engine

The decision engine intentionally uses controlled outcomes.

## RESOLVE

Used when the request is sufficiently understood and the official policy provides a safe resolution path.

Example:

```text
Employee:
"I need guest Wi-Fi tomorrow."

Decision:
RESOLVE

Reason:
Guest Wi-Fi credentials can be generated by an employee
at the front-desk kiosk and do not require an IT ticket.
```

---

## CLARIFY

Used when the system does not have enough information to safely determine the appropriate action.

Example:

```text
Employee:
"Hey, can you help? It's not working."

Decision:
CLARIFY

Reason:
The affected system/device and symptom are unknown.
```

The agent should gather the minimum information necessary before proceeding.

---

## ESCALATE

Used when the request is:

* security-sensitive
* risky
* outside IT authority
* dependent on another department
* unclear after reasonable clarification
* inappropriate for automatic resolution

Example:

```text
Employee:
"I received a phishing email."

Decision:
ESCALATE

Reason:
Security incident reporting requires immediate escalation
to the designated Security channel.
```

---

# Safety & Guardrails

The prototype is intentionally conservative around high-risk requests.

### Security incidents

Suspected:

* phishing
* malware
* unauthorized access

are handled as security-sensitive events.

The agent does not encourage employees to distribute suspicious content to other employees.

### Unauthorized access

The system does not invent approval authority or grant privileged access simply because an employee describes the request as urgent.

### Ambiguous requests

The agent does not fabricate an answer when the request is insufficiently specified.

Instead:

```text
Unknown → Clarify
```

### Cross-functional requests

If the supplied policy assigns responsibility to another department, the agent does not pretend IT owns that decision.

---

# Historical Ticket Context

The supplied ticket queue is used as **historical precedent**, not as a replacement for policy.

For example:

```text
Policy Evidence
      +
Historical Precedent
      ↓
Decision Context
```

This allows the system to provide consistency with previous cases while maintaining the distinction between:

**What the company policy says**

and

**What happened in a previous ticket.**

---

# Structured Ticketing

When escalation or ticket creation is required, the prototype generates structured records containing fields such as:

```text
ticket_id
timestamp
employee_name
employee_email
employee_id
issue_type
priority
status
description
policy_source
decision
escalation_reason
audit_status
```

This demonstrates how the prototype could later integrate with enterprise ticketing platforms such as ServiceNow or Jira.

The current implementation intentionally uses a local JSON store rather than modifying a real IT service-management system.

---

# Audit Trail

Every meaningful agent action can be recorded in an append-only JSONL audit log.

Typical events include:

```text
REQUEST_RECEIVED
CLASSIFIED
POLICY_RETRIEVED
FOLLOW_UP_REQUESTED
DECISION_MADE
TICKET_CREATED
ESCALATED
RESOLVED
USER_RESPONSE
```

The audit trail provides:

* traceability
* debugging visibility
* decision reconstruction
* evaluator transparency
* a foundation for production observability

Streamlit page rendering itself is not treated as a business action, preventing meaningless audit-event inflation.

---

# Streamlit Interface

The application provides an enterprise-style operations console rather than a generic chatbot interface.

### Main sections

```text
Chat
Batch QA
Ticket Queue
Audit Trail
Architecture / About
```

### Chat

Provides:

* employee context
* request input
* issue classification
* risk level
* decision
* policy evidence
* historical precedent
* resolution / clarification / escalation
* ticket details
* technical trace

### Batch QA

Allows the supplied employee request set to be exercised systematically.

### Ticket Queue

Provides visibility into generated and historical tickets.

### Audit Trail

Provides an inspectable timeline of meaningful agent actions.

### Theme

The interface supports:

* Dark mode
* Light mode

with a restrained enterprise/cyberpunk visual system.

---

# Example Scenarios

The official request set contains 15 employee scenarios covering common IT-support situations.

Representative scenarios include:

### Guest Wi-Fi

```text
Request:
"I need guest Wi-Fi tomorrow."

Flow:
Request
→ Guest Wi-Fi classification
→ KB-07 retrieval
→ RESOLVE
→ No unnecessary IT ticket
```

### Expired VPN credentials

```text
Request:
"My VPN stopped working and my credentials expired."

Flow:
Request
→ VPN classification
→ KB-02 retrieval
→ Historical context
→ Resolution / appropriate action
→ Audit
```

### Non-catalog software

```text
Request:
"I need approval to install a data-analysis tool that isn't in the catalog."

Flow:
Request
→ Software classification
→ KB-04 retrieval
→ Security review identified
→ Appropriate decision
→ Audit
```

### Phishing

```text
Request:
"I received a phishing email."

Flow:
Request
→ Security classification
→ KB-09 retrieval
→ HIGH-RISK handling
→ ESCALATE
→ Security reporting path
→ Audit
```

### Ambiguous request

```text
Request:
"Hey, can you help? It's not working."

Flow:
Request
→ Unknown classification
→ Insufficient information
→ CLARIFY
```

---

# Technology Stack

```text
Python
Streamlit
scikit-learn
Pytest
JSON
JSONL
Markdown
```

### Why no external LLM API?

The current runtime deliberately does **not require an external LLM API or API key**.

This design prioritizes:

* deterministic behavior
* reproducibility
* low deployment friction
* policy traceability
* predictable testing
* reliable demonstration within the assignment constraints

The architecture can later introduce an LLM as an additional reasoning layer while retaining deterministic policy/risk guardrails.

---

# Architecture

```text
┌─────────────────────────────────────┐
│          Streamlit UI               │
│ Chat | QA | Tickets | Audit         │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│        Agent Orchestrator            │
│ Observe → Classify → Assess → Decide│
└───────────────┬───────────────┬─────┘
                │               │
                ▼               ▼
       ┌────────────────┐ ┌─────────────────┐
       │ Policy Search  │ │ Ticket Context  │
       │ TF-IDF /       │ │ Historical      │
       │ Similarity     │ │ Precedent       │
       └───────┬────────┘ └────────┬────────┘
               │                   │
               └─────────┬─────────┘
                         ▼
              ┌────────────────────┐
              │ Risk & Decision     │
              │ Engine              │
              └─────────┬──────────┘
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
          RESOLVE    CLARIFY    ESCALATE
             │          │          │
             └──────────┼──────────┘
                        ▼
              ┌────────────────────┐
              │ Ticket / Action    │
              └─────────┬──────────┘
                        ▼
              ┌────────────────────┐
              │ Audit Trail        │
              └────────────────────┘
```

---

# Project Structure

```text
internal_it_service_agent/
│
├── app.py
├── agent.py
├── models.py
├── tools.py
├── requirements.txt
├── README.md
│
├── policies/
│   └── it_policy.md
│
├── data/
│   ├── tickets.json
│   └── audit_log.jsonl
│
└── tests/
    └── test_agent.py
```

---

# Installation

## 1. Clone the repository

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd internal_it_service_agent
```

## 2. Create a virtual environment

### Windows

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

# Run the Application

```bash
streamlit run app.py
```

Or:

```bash
python -m streamlit run app.py
```

The application will open in the local browser.

---

# Run Tests

```bash
pytest -q
```

The test suite covers agent behavior including:

* issue classification
* policy retrieval
* clarification
* resolution
* escalation
* ticket generation
* audit logging
* multi-turn state
* security-sensitive requests
* ambiguous requests
* official employee scenarios

---

# Configuration

The prototype is designed to run locally without external API credentials.

An `.env` file should not be committed if future integrations require secrets.

Example environment template:

```text
.env.example
```

Never commit API keys, passwords, tokens, or credentials.

---

# Deployment

The application is designed to be compatible with **Streamlit Community Cloud**.

Deployment concept:

```text
GitHub Repository
       │
       ▼
Streamlit Community Cloud
       │
       ▼
     app.py
       │
       ├── Agent
       ├── Policies
       ├── Ticket Store
       └── Audit Trail
```

See:

```text
docs/streamlit_deployment.md
```

for deployment instructions when available.

---

# Evaluation-Oriented Design

This project is intentionally designed around the core requirements of the AIONOS Internal Service Agent assignment.

| Requirement                   | Project Capability     |
| ----------------------------- | ---------------------- |
| Understand employee issue     | Intent Router          |
| Find relevant policy          | Policy Retrieval       |
| Ask follow-up questions       | Stateful Clarification |
| Resolve simple requests       | Resolution Engine      |
| Escalate risky requests       | Risk Engine            |
| Create structured ticket      | Ticket Store           |
| Show source used              | Policy Evidence Panel  |
| Maintain audit trail          | JSONL Audit Trail      |
| Demonstrate working prototype | Streamlit UI           |
| Validate scenarios            | Batch QA               |

---

# Testing Philosophy

The project does not consider:

```text
"Application starts successfully"
```

to be sufficient testing.

Behavioral validation is more important.

The system should be evaluated against:

```text
Normal Requests
      +
Ambiguous Requests
      +
High-Risk Requests
      +
Cross-Functional Requests
      +
Security Requests
      +
Multi-Turn Requests
```

The objective is to verify that the agent selects the **appropriate controlled action**, rather than merely producing text.

---

# Current Limitations

This is an assignment prototype rather than a production ITSM platform.

Current limitations include:

* Local JSON ticket storage
* Local JSONL audit storage
* No real ServiceNow/Jira integration
* No real employee directory integration
* No real email dispatch
* No real identity/authentication system
* Deterministic issue classification
* Local policy repository
* Simulated escalation

These limitations are intentional for the prototype scope.

---

# Production Evolution

A production implementation could evolve into:

```text
                 Employee
                    │
                    ▼
             Enterprise Portal
                    │
                    ▼
              Agent Gateway
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       Identity   Policy    Ticketing
       / RBAC     Engine    Platform
                    │
                    ▼
             Agent Orchestrator
                    │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
       Resolve    Clarify    Escalate
                    │
                    ▼
             Human-in-the-loop
                    │
                    ▼
               Audit / SIEM
```

Potential future enhancements:

* ServiceNow/Jira integration
* enterprise SSO
* RBAC
* vector database retrieval
* LLM-based intent extraction
* retrieval-augmented generation
* human-in-the-loop approval
* observability dashboards
* evaluation/monitoring pipelines
* policy versioning
* enterprise knowledge connectors

An LLM could be introduced as a controlled reasoning/interface layer while keeping **policy retrieval, authorization boundaries, risk rules and auditability deterministic wherever appropriate**.

---

# Design Principles

The project follows five core principles:

### 1. Ground before answering

Retrieve organizational evidence before giving policy-sensitive guidance.

### 2. Clarify before guessing

Missing information should result in a targeted question rather than hallucinated assumptions.

### 3. Escalate before taking unsafe action

Security-sensitive or unauthorized operations should not be automatically executed.

### 4. Separate policy from precedent

Historical tickets provide context; official policies remain the authoritative source.

### 5. Audit every meaningful action

Important decisions should be reconstructable after the interaction.

---

# Project Philosophy

This project treats an AI service agent as an **orchestration system**, not merely a conversational model.

The important question is not:

> "Can the AI answer the employee?"

It is:

> **"Can the system make the right kind of controlled decision, based on available organizational evidence, and explain what happened?"**

That distinction drives the architecture of this project.

---

# AIONOS Agentic AI Factory — Round 1

**Assignment:** Assignment 2 — Internal Service Agent
**Domain:** IT Support
**Organization in Data Pack:** Veridian Corp
**Interface:** Streamlit
**Runtime:** Python
**Architecture:** Policy-Grounded Agentic Workflow

---

## Author

**Sankalp Sharma**

B.Tech — Computer Science / Artificial Intelligence & Machine Learning

---

## License

This project was created as part of an AIONOS Agentic AI Factory assessment exercise.

The supplied Veridian Corp assignment data is used solely for the purposes of the assessment prototype.

---
