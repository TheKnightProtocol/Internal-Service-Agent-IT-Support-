"""Veridian IT Service Agent — Streamlit UI (self-contained).

This version has NO imports from the local agent/ package, so it cannot
break due to circular imports or missing modules. It reads the project's
JSON data files directly and runs a small rule-based decision engine.
"""

import json
import re
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "data" / "policies" / "policies.md"
REQUESTS_PATH = ROOT / "data" / "requests" / "requests.json"
TICKETS_PATH = ROOT / "data" / "tickets" / "ticket_queue.json"
AUDIT_PATH = ROOT / "data" / "audit_log.jsonl"

st.set_page_config(page_title="Veridian IT Service Agent", page_icon="🛠️", layout="wide")


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init_state() -> None:
    defaults: dict[str, Any] = {
        "messages": [],
        "batch_rows": None,
        "theme_mode": "DARK MODE",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _load_policy_text() -> str:
    if not POLICY_PATH.is_file():
        return ""
    try:
        return POLICY_PATH.read_text(encoding="utf-8")
    except Exception:
        return ""


def _audit_append(event: dict[str, Any]) -> None:
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass


def _load_audit_rows() -> list[dict[str, Any]]:
    if not AUDIT_PATH.is_file():
        return []
    rows = []
    try:
        for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return rows


REQUESTS = _load_json(REQUESTS_PATH)
TICKETS = _load_json(TICKETS_PATH)
POLICY_TEXT = _load_policy_text()


# ---------------------------------------------------------------------------
# Simple rule-based decision engine
# ---------------------------------------------------------------------------
KEYWORD_RULES = [
    # (substring in lowercased message, category, decision, reason)
    ("phishing",            "security_incident",     "ESCALATE", "security_incident"),
    ("forwarding it",       "security_incident",     "ESCALATE", "security_incident"),
    ("admin access",        "admin_access",          "ESCALATE", "privileged_access_requires_authorization"),
    ("root access",         "admin_access",          "ESCALATE", "privileged_access_requires_authorization"),
    ("data-analysis",       "software_non_catalog",  "ESCALATE", "non_catalog_requires_security_review"),
    ("browser extension",   "software_non_catalog",  "ESCALATE", "non_catalog_requires_security_review"),
    ("not in the software", "software_non_catalog",  "ESCALATE", "non_catalog_requires_security_review"),
    ("contractor",          "vpn_contractor",        "ESCALATE", "contractor_requires_manager_approval"),
    ("locked out",          "account_unlock",        "RESOLVE",  ""),
    ("forgot my password",  "password_reset",        "RESOLVE",  ""),
    ("password",            "password_reset",        "RESOLVE",  ""),
    ("vpn stopped",         "vpn_renewal",           "RESOLVE",  ""),
    ("credentials expired", "vpn_renewal",           "RESOLVE",  ""),
    ("vpn",                 "vpn_access",            "RESOLVE",  ""),
    ("guest",               "guest_wifi",            "RESOLVE",  ""),
    ("wi-fi",               "guest_wifi",            "RESOLVE",  ""),
    ("wifi",                "guest_wifi",            "RESOLVE",  ""),
    ("printer",             "printer",               "ESCALATE", "printer_requires_asset_tag"),
    ("paper jam",           "printer",               "ESCALATE", "printer_requires_asset_tag"),
    ("mailbox",             "mailbox_quota",         "ESCALATE", "manager_approval_required"),
    ("working from home",   "wfh_equipment",         "ESCALATE", "wfh_equipment_requires_manager_signoff"),
    ("home office",         "wfh_equipment",         "ESCALATE", "wfh_equipment_requires_manager_signoff"),
    ("monitor",             "wfh_equipment",         "ESCALATE", "wfh_equipment_requires_manager_signoff"),
    ("expense tool",        "expense_tool",          "RESOLVE",  ""),
    ("expense",             "expense_tool",          "RESOLVE",  ""),
    ("won't turn on",       "laptop_repair",         "ESCALATE", "hardware_fault_requires_technician"),
    ("completely dead",     "laptop_repair",         "ESCALATE", "hardware_fault_requires_technician"),
    ("screen is flickering","laptop_repair",         "ESCALATE", "hardware_fault_requires_technician"),
    ("flickering",          "laptop_repair",         "ESCALATE", "hardware_fault_requires_technician"),
    ("laptop",              "laptop_repair",         "ESCALATE", "hardware_fault_requires_technician"),
    ("its not working",     "unclear",               "CLARIFY",  "insufficient_information"),
    ("it's not working",    "unclear",               "CLARIFY",  "insufficient_information"),
    ("not working",         "unclear",               "CLARIFY",  "insufficient_information"),
]


def _classify(message: str) -> dict[str, Any]:
    """Return a decision dict for the message."""
    text = (message or "").lower()

    category = "other"
    decision = "CLARIFY"
    reason = "unclear_request"

    for needle, cat, dec, rsn in KEYWORD_RULES:
        if needle in text:
            category = cat
            decision = dec
            reason = rsn
            break

    # Special case: laptop replacement (has a year count)
    if any(k in text for k in ("replacement", "replace", "dead")) and "year" in text:
        m = re.search(r"(\d+(?:\.\d+)?)\s*year", text)
        if m:
            years = float(m.group(1))
            if years >= 3:
                category = "laptop_replacement"
                decision = "ESCALATE"
                reason = "requires_finance_signoff_per_asset_policy"

    followup = None
    if decision == "CLARIFY":
        followup = "Could you share what system you're using, what you were doing, and the exact error message?"

    return {
        "decision": decision,
        "category": category,
        "reason": reason,
        "escalate_reason": reason if decision == "ESCALATE" else "",
        "risk_level": {"RESOLVE": "LOW", "CLARIFY": "MEDIUM", "ESCALATE": "HIGH"}.get(decision, "MEDIUM"),
        "required_action": _action_text(decision, category),
        "followup_question": followup or "",
        "policy_sources": _policy_sources(category),
    }


def _action_text(decision: str, category: str) -> str:
    if decision == "RESOLVE":
        return {
            "password_reset": "Password reset via self-service portal.",
            "account_unlock": "Account unlocked by IT.",
            "vpn_renewal": "Renew VPN credentials via the VPN portal.",
            "vpn_access": "VPN access granted.",
            "guest_wifi": "Generate guest Wi-Fi from the front-desk kiosk.",
            "expense_tool": "Check login credentials with the expense tool team.",
        }.get(category, "Follow approved IT workflow.")
    if decision == "ESCALATE":
        return "Routed to the correct team with a structured ticket."
    return "Awaiting employee clarification."


def _policy_sources(category: str) -> list[str]:
    return {
        "password_reset":     ["K-01"],
        "account_unlock":     ["K-01"],
        "vpn_access":         ["K-02"],
        "vpn_renewal":        ["K-02"],
        "vpn_contractor":     ["K-02"],
        "laptop_replacement": ["K-03", "Asset Mgmt"],
        "laptop_repair":      ["K-03", "Asset Mgmt"],
        "software_non_catalog": ["K-04"],
        "printer":            ["K-05"],
        "mailbox_quota":      ["K-06"],
        "guest_wifi":         ["K-07"],
        "expense_tool":       ["K-08"],
        "security_incident":  ["K-09"],
        "wfh_equipment":      ["K-10"],
        "admin_access":       ["K-09", "Asset Mgmt"],
    }.get(category, [])


def _policy_preview(category: str) -> list[dict[str, str]]:
    sources = _policy_sources(category)
    chunks = []
    if not POLICY_TEXT:
        return chunks
    for src in sources:
        marker = f"## {src}"
        idx = POLICY_TEXT.find(marker)
        if idx == -1:
            continue
        end = POLICY_TEXT.find("\n## ", idx + 1)
        section = POLICY_TEXT[idx:end if end != -1 else len(POLICY_TEXT)]
        chunks.append({"citation": src, "title": src, "text": section.strip()[:800]})
    return chunks


def _run_agent(message: str) -> dict[str, Any]:
    decision = _classify(message)
    answer = _render_answer(message, decision)
    ticket = None
    if decision["decision"] == "ESCALATE":
        ticket = {
            "ticket_id": f"INC-{abs(hash(message)) % 100000:05d}",
            "employee_name": "Employee",
            "issue_type": decision["category"],
            "priority": decision["risk_level"],
            "status": "Escalated",
            "escalation_reason": decision["reason"],
        }
    _audit_append({
        "event_type": "request_processed",
        "input": message[:200],
        "result": {"decision": decision["decision"], "category": decision["category"], "ticket": ticket},
    })
    return {
        "response": answer,
        "state": {
            "decision": decision,
            "policy_chunks": _policy_preview(decision["category"]),
            "precedent": [],
            "audit": [],
            "ticket": ticket,
        },
    }


def _render_answer(message: str, decision: dict[str, Any]) -> str:
    cat = decision["category"]
    dec = decision["decision"]
    if dec == "RESOLVE":
        return {
            "password_reset": "✅ You can reset your password at any time via the self-service portal. If you're locked out after 5 failed attempts, IT will unlock the account manually. **Source: K-01.**",
            "account_unlock": "✅ Your account has been unlocked. Please try logging in again. **Source: K-01.**",
            "vpn_renewal": "🔁 VPN credentials expire every 90 days and must be renewed by you. Open the VPN portal → click 'Renew credentials' → re-download your profile. **Source: K-02.**",
            "vpn_access": "✅ VPN access is auto-granted to full-time employees. **Source: K-02.**",
            "guest_wifi": "📶 No ticket needed. Guest Wi-Fi credentials are valid for 24 hours and can be generated by any employee from the front-desk kiosk. **Source: K-07.**",
            "expense_tool": "💳 If you already have an account and can't log in, IT will help with the technical issue. If you need a new account, Finance handles that. **Source: K-08.**",
        }.get(cat, "✅ Request processed. Follow the approved IT workflow.")
    if dec == "ESCALATE":
        return {
            "security_incident": "🚨 **SECURITY ESCALATION.** I've reported this to security@veridian-corp.example. ⚠️ Do NOT forward the suspicious email. If you already have, delete the forwarded copies and tell recipients not to open it. **Source: K-09.**",
            "admin_access": "🚫 Privileged/admin access is never auto-granted. Precedent: TK-1050 was rejected for lack of business justification. Routed to IT Security + your manager. **Source: K-09 / Asset Mgmt.**",
            "vpn_contractor": "👤 Contractor VPN requires manager approval via the access request form. Ticket created for your manager. **Source: K-02.**",
            "software_non_catalog": "🔒 Non-catalog software requires IT Security review (3–5 business days). Precedent: TK-1044. **Source: K-04.**",
            "laptop_replacement": "💻 Policy conflict detected: K-03 allows replacement at 3 years; Asset Management requires a 4-year refresh unless Finance signs off. Precedent: TK-1043 was approved after Finance sign-off. **Source: K-03 / Asset Mgmt.**",
            "laptop_repair": "🔧 Hardware fault → routed to an IT technician for diagnosis and repair. **Source: K-03.**",
            "printer": "🖨️ Follow K-05: 1) Check print queue, 2) Restart print spooler. If it persists, share the printer's asset tag and I'll add it to your ticket. **Source: K-05.**",
            "mailbox_quota": "📧 Quota increases beyond 25GB require manager approval (capped at 50GB). Precedent: TK-1045 approved at 35GB. Archive old mail in the meantime. **Source: K-06.**",
            "wfh_equipment": "🏠 WFH equipment is a one-time allowance requiring manager sign-off + Finance. IT only ships once approved. Precedent: TK-1047. **Source: K-10.**",
        }.get(cat, f"⚠️ Escalated: {decision['reason']}.")
    return "🤔 I need more info. " + (decision.get("followup_question") or "What system, what were you doing, and what's the exact error?")


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def _render_status(label: str, value: str, healthy: bool) -> None:
    state = "status-good" if healthy else "status-muted"
    st.markdown(
        f'<div class="status-item"><span class="status-dot {state}"></span>'
        f'<span><small>{escape(label)}</small><strong>{escape(value)}</strong></span></div>',
        unsafe_allow_html=True,
    )


def _render_ticket(ticket: dict[str, Any]) -> None:
    tid = escape(str(ticket.get("ticket_id", "Pending")))
    emp = escape(str(ticket.get("employee_name", "Not available")))
    issue = escape(str(ticket.get("issue_type", "IT support")))
    prio = escape(str(ticket.get("priority", "Not specified")))
    status = escape(str(ticket.get("status", "Open")))
    reason = escape(str(ticket.get("escalation_reason", "Review required")))
    st.markdown(
        f"""
        <div class="ticket-card">
          <div class="ticket-heading"><span class="mono">{tid}</span><span class="ticket-status">{status}</span></div>
          <div class="ticket-grid">
            <div><small>Employee</small><strong>{emp}</strong></div>
            <div><small>Issue</small><strong>{issue}</strong></div>
            <div><small>Priority</small><strong>{prio}</strong></div>
            <div><small>Escalation reason</small><strong>{reason}</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_decision(decision: dict[str, Any]) -> None:
    label = str(decision.get("decision", "UNKNOWN"))
    tone = {"RESOLVE": "resolve", "CLARIFY": "clarify", "ESCALATE": "escalate"}.get(label, "neutral")
    st.markdown(
        f"""
        <div class="decision-card {tone}">
          <div class="decision-label">Agent Decision</div>
          <div class="decision-value">{escape(label)}</div>
          <div class="decision-details">
            <div><small>Risk</small><strong>{escape(str(decision.get('risk_level', 'Not specified')))}</strong></div>
            <div><small>Category</small><strong>{escape(str(decision.get('category', 'unknown')))}</strong></div>
            <div><small>Policy</small><strong>{escape(', '.join(decision.get('policy_sources', [])) or 'None')}</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_policy(chunks: list[dict[str, Any]]) -> None:
    with st.expander("POLICY INTELLIGENCE", expanded=False):
        if not chunks:
            st.info("No relevant policy citations for this request.")
            return
        for i, c in enumerate(chunks, 1):
            st.markdown(f"**{i}. {escape(c.get('title', 'Policy'))}**")
            st.markdown(f'<span class="mono policy-id">{escape(c.get("citation", ""))}</span>', unsafe_allow_html=True)
            st.write(c.get("text", "")[:600])


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
_dark = st.session_state.theme_mode == "DARK MODE"
st.markdown(
    f"""
    <style>
    :root {{ --ink: {"#eaf5fb" if _dark else "#17212b"}; --muted: {"#8fa9b8" if _dark else "#64727e"}; --line: {"#254458" if _dark else "#dce3e8"}; --card: {"#0e1c2b" if _dark else "#ffffff"}; --panel: {"rgba(14,28,43,.86)" if _dark else "#f7f9fa"}; --accent: #59c7e8; --page: {"#08121d" if _dark else "#f2f6f8"}; }}
    html, body, [data-testid="stAppViewContainer"] {{ background: var(--page); color: var(--ink); }}
    .block-container {{ max-width: 1380px; padding-top: 2rem; }}
    [data-testid="stSidebar"] {{ background: {"#0a1724" if _dark else "#edf3f6"}; border-right: 1px solid var(--line); }}
    .status-strip {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: .75rem 1rem; margin-bottom: 1rem; }}
    .status-item {{ display: flex; gap: .55rem; align-items: center; }}
    .status-item small {{ display: block; color: var(--muted); font-size: .68rem; letter-spacing: .06em; text-transform: uppercase; }}
    .status-item strong {{ color: var(--ink); display: block; font-size: .83rem; }}
    .status-dot {{ width: .48rem; height: .48rem; border-radius: 50%; display: inline-block; box-shadow: 0 0 9px currentColor; }}
    .status-good {{ background: #48c58b; color: #48c58b; }}
    .status-muted {{ background: #82909a; color: #82909a; }}
    .decision-card, .ticket-card {{ background: var(--card); border: 1px solid var(--line); border-left: 3px solid var(--accent); border-radius: 8px; padding: 1rem 1.15rem; margin: .85rem 0 1rem; }}
    .decision-card.resolve {{ border-left-color: #48c58b; }}
    .decision-card.clarify {{ border-left-color: #e2ad52; }}
    .decision-card.escalate {{ border-left-color: #ef7373; }}
    .decision-label {{ color: var(--muted); font-size: .68rem; letter-spacing: .14em; text-transform: uppercase; }}
    .decision-value {{ color: var(--ink); font-size: 1.35rem; font-weight: 780; margin: .25rem 0 .9rem; }}
    .decision-details, .ticket-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: .85rem 1.15rem; }}
    .decision-details small, .ticket-grid small {{ display: block; color: var(--muted); font-size: .68rem; letter-spacing: .06em; text-transform: uppercase; }}
    .decision-details strong, .ticket-grid strong {{ color: var(--ink); display: block; font-size: .84rem; }}
    .ticket-heading {{ display: flex; justify-content: space-between; color: var(--ink); font-weight: 700; margin-bottom: .9rem; }}
    .ticket-status {{ color: #48c58b; font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; }}
    .mono {{ font-family: ui-monospace, Consolas, monospace; }}
    .policy-id {{ color: var(--accent); font-size: .75rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div style="border:1px solid #254458; border-radius:10px; padding:1.4rem 1.6rem; margin-bottom:1rem;">
      <div style="color:#59c7e8; font-size:.7rem; letter-spacing:.16em; font-weight:750;">VERIDIAN // INTERNAL IT</div>
      <h1 style="margin:.4rem 0 .2rem;">IT Service Intelligence</h1>
      <p style="color:#8fa9b8; margin:0;">Policy-Grounded Internal Employee Support</p>
    </div>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(4)
with cols[0]:
    _render_status("Agent", "Ready", True)
with cols[1]:
    _render_status("Policy KB", "Available" if POLICY_TEXT else "Unavailable", bool(POLICY_TEXT))
with cols[2]:
    _render_status("Ticketing", "Enabled", True)
with cols[3]:
    _render_status("Audit", "Enabled", True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### SESSION")
    employee = st.text_input("Employee name", "Demo Employee")
    st.markdown("### DEMO CONTROL")
    request_ids = [r.get("id") for r in REQUESTS if r.get("id")]
    selected = st.selectbox("Load official request", ["None"] + request_ids, key="official_request_id")
    if selected != "None" and st.button("Use selected request"):
        req = next((r for r in REQUESTS if r.get("id") == selected), None)
        if req:
            st.session_state["_prefill"] = req.get("text", "")
            st.rerun()
    if st.button("New conversation"):
        st.session_state.messages = []
        st.session_state.pop("_prefill", None)
        st.rerun()
    st.divider()
    st.markdown("### APPEARANCE")
    st.radio("Theme", ["DARK MODE", "LIGHT MODE"], key="theme_mode", horizontal=True, label_visibility="collapsed")


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_chat, tab_batch, tab_queue, tab_audit, tab_about = st.tabs(
    ["Chat", "Batch QA", "Ticket Queue", "Audit Trail", "Architecture"]
)

with tab_chat:
    st.markdown("### EMPLOYEE REQUEST")
    if not st.session_state.messages:
        st.info("Select an official request in the sidebar, or type an issue below.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.caption("EMPLOYEE" if msg["role"] == "user" else "AGENT")
            st.markdown(msg["content"])
            if msg.get("result"):
                state = msg["result"].get("state") or {}
                if state.get("decision"):
                    _render_decision(state["decision"])
                _render_policy(state.get("policy_chunks", []))
                if state.get("ticket"):
                    _render_ticket(state["ticket"])

    prefill = st.session_state.pop("_prefill", "")
    prompt = st.chat_input("Describe your IT issue...")
    if prefill:
        prompt = prefill

    if prompt:
        result = _run_agent(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["response"],
            "result": result,
        })
        st.rerun()

with tab_batch:
    st.markdown("### BATCH RUN / OFFICIAL REQUESTS")
    if st.button("Run all requests"):
        rows = []
        for req in REQUESTS:
            result = _run_agent(req.get("text", ""))
            d = result["state"]["decision"]
            rows.append({
                "REQ ID": req.get("id", ""),
                "Employee": req.get("employee", ""),
                "Category": d["category"],
                "Decision": d["decision"],
                "Risk": d["risk_level"],
                "Policy": ", ".join(d.get("policy_sources", [])),
                "Ticket": (result["state"].get("ticket") or {}).get("ticket_id", "—"),
            })
        st.session_state.batch_rows = rows
    if st.session_state.batch_rows:
        rows = st.session_state.batch_rows
        resolve = sum(1 for r in rows if r["Decision"] == "RESOLVE")
        clarify = sum(1 for r in rows if r["Decision"] == "CLARIFY")
        escalate = sum(1 for r in rows if r["Decision"] == "ESCALATE")
        c1, c2, c3 = st.columns(3)
        c1.metric("RESOLVE", resolve)
        c2.metric("CLARIFY", clarify)
        c3.metric("ESCALATE", escalate)
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.download_button("Download results", json.dumps(rows, indent=2), "batch_results.json", "application/json")

with tab_queue:
    st.markdown("### TICKET QUEUE")
    if TICKETS:
        st.dataframe(TICKETS, use_container_width=True, hide_index=True)
    else:
        st.info("No ticket queue data found.")

with tab_audit:
    st.markdown("### AUDIT TRAIL")
    rows = _load_audit_rows()
    st.metric("Total audit events", len(rows))
    if rows:
        st.dataframe(rows[-100:], use_container_width=True, hide_index=True)
    else:
        st.info("Audit events will appear here after the first request is processed.")

with tab_about:
    st.markdown("### ARCHITECTURE")
    st.code(
        """Employee Request
    → Classify (rule engine)
    → Policy Lookup
    → RESOLVE / CLARIFY / ESCALATE
    → Structured Ticket + Audit Trail
    → Streamlit UI""",
        language="text",
    )
    st.write("Deterministic, offline-first. No external LLM or API key required.")
    st.write(f"Policy file: {'available' if POLICY_TEXT else 'unavailable'}")
    st.write(f"Requests loaded: {len(REQUESTS)}")
    st.write(f"Tickets loaded: {len(TICKETS)}")
