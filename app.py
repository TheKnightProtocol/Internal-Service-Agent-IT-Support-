import json
import os
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from agent import ITServiceAgent

ROOT = Path(__file__).parent
POLICY_PATH = ROOT / "data" / "policies" / "policies.md"
TICKET_STORE_PATH = ROOT / "data" / "tickets.json"
AUDIT_PATH = ROOT / "data" / "audit_log.jsonl"
st.set_page_config(page_title="Veridian IT Service Agent", page_icon="IT", layout="wide")


def _init_state() -> None:
    defaults: dict[str, Any] = {
        "agent": None,
        "messages": [],
        "pending_submission": None,
        "pending_batch": False,
        "batch_rows": None,
        "theme_mode": "DARK MODE",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_state()

if st.session_state.agent is None:
    st.session_state.agent = ITServiceAgent()
agent = st.session_state.agent


def _load_json(filename: str) -> list[dict[str, Any]]:
    try:
        data = json.loads((ROOT / filename).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _load_yaml(filename: str) -> list[dict[str, Any]]:
    try:
        data = yaml.safe_load((ROOT / filename).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    return data if isinstance(data, list) else []


def _load_audit_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not AUDIT_PATH.is_file():
        return rows
    try:
        lines = AUDIT_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        result = event.get("result") or {}
        if not isinstance(result, dict):
            result = {"detail": str(result)}
        rows.append({
            "Event": event.get("event_type", "UNKNOWN"),
            "Timestamp": event.get("timestamp", ""),
            "Request": result.get("input", ""),
            "Decision": result.get("decision", result.get("status", "")),
            "Ticket": result.get("ticket", ""),
        })
    return rows


def _health_checks() -> dict[str, bool]:
    policy_ok = POLICY_PATH.is_file() and os.access(POLICY_PATH, os.R_OK)
    ticket_ok = TICKET_STORE_PATH.is_file() and os.access(TICKET_STORE_PATH, os.R_OK)
    audit_ok = AUDIT_PATH.parent.is_dir() and os.access(AUDIT_PATH.parent, os.W_OK)
    return {"policy": policy_ok, "tickets": ticket_ok, "audit": audit_ok}


requests = _load_json("data/requests/requests.json")
eval_cases = {case.get("id"): case for case in _load_yaml("evals/test_cases.yaml") if case.get("id")}


def _safe_handle(prompt: str, employee_data: dict[str, Any]) -> dict[str, Any]:
    try:
        result = agent.handle(prompt, employee_data)
    except Exception as error:
        return {
            "response": "The request could not be processed. Please try again or escalate to the IT Service Desk.",
            "state": {},
        }
    return result if isinstance(result, dict) else {"response": "No response produced.", "state": {}}


def _queue_submission(prompt: str, employee_data: dict[str, Any]) -> None:
    if prompt.strip():
        st.session_state.pending_submission = {
            "prompt": prompt.strip(),
            "employee": dict(employee_data),
        }


def _process_pending_submission() -> None:
    submission = st.session_state.pop("pending_submission", None)
    if not isinstance(submission, dict):
        return
    prompt = submission.get("prompt")
    employee_data = submission.get("employee")
    if not isinstance(prompt, str) or not isinstance(employee_data, dict):
        return
    result = _safe_handle(prompt, employee_data)
    st.session_state.messages.extend([
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": result.get("response", "No response produced."), "result": result},
    ])

def _run_batch() -> None:
    st.session_state.pending_batch = False
    batch_agent = ITServiceAgent()
    rows: list[dict[str, Any]] = []
    for request in requests:
        result = _safe_handle_with_agent(
            batch_agent,
            request.get("text", ""),
            {"name": request.get("employee", "Employee"), "employee_id": request.get("id")},
        )
        state = result.get("state") or {}
        decision = state.get("decision") or {}
        ticket = state.get("ticket")
        status = "ESCALATE" if ticket else "CLARIFY" if decision.get("needs_followup") else "RESOLVE"
        rows.append({
            "REQ ID": request.get("id", ""),
            "Employee": request.get("employee", ""),
            "Issue": decision.get("category", ""),
            "Decision": status,
            "Risk": decision.get("risk_level", ""),
            "Policy": ", ".join(decision.get("policy_sources", [])),
            "Ticket": ticket.get("ticket_id", "") if isinstance(ticket, dict) else "NO",
            "Status": _batch_status(request, result, eval_cases.get(request.get("id"))),
        })
    st.session_state.batch_rows = rows


def _safe_handle_with_agent(
    target_agent: ITServiceAgent,
    prompt: str,
    employee_data: dict[str, Any],
) -> dict[str, Any]:
    try:
        result = target_agent.handle(prompt, employee_data)
    except Exception as error:
        return {
            "response": "The request could not be processed. Please try again or escalate to the IT Service Desk.",
            "state": {},
        }
    return result if isinstance(result, dict) else {"response": "No response produced.", "state": {}}

def _value(data: Any, key: str, default: Any = "") -> Any:
    if isinstance(data, dict):
        return data.get(key, default)
    return default

def _render_ticket(ticket: dict[str, Any]) -> None:
    st.markdown('<div class="eyebrow">SERVICE TICKET</div>', unsafe_allow_html=True)
    ticket_id = escape(str(_value(ticket, "ticket_id", "Pending")))
    employee_name = escape(str(_value(ticket, "employee_name", "Not available")))
    issue = escape(str(_value(ticket, "issue_type", _value(ticket, "category", "IT support"))))
    priority = escape(str(_value(ticket, "priority", "Not specified")))
    status = escape(str(_value(ticket, "status", "Open")))
    reason = escape(str(_value(ticket, "escalation_reason", "Review required")))
    st.markdown(
        f"""
                <div class="ticket-card glow-border">
                    <div class="ticket-heading"><span class="mono">{ticket_id}</span><span class="ticket-status">{status}</span></div>
          <div class="ticket-grid">
            <div><small>Employee</small><strong>{employee_name}</strong></div>
            <div><small>Issue</small><strong>{issue}</strong></div>
            <div><small>Priority</small><strong>{priority}</strong></div>
            <div><small>Escalation reason</small><strong>{reason}</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Technical Details", expanded=False):
        st.json(ticket)


def _render_decision(state: dict[str, Any]) -> None:
    decision = _value(state, "decision", {})
    if not isinstance(decision, dict) or not decision:
        return
    label = str(_value(decision, "decision", "UNKNOWN"))
    tone = {"RESOLVE": "resolve", "CLARIFY": "clarify", "ESCALATE": "escalate"}.get(label, "neutral")
    risk = escape(str(_value(decision, "risk_level", "Not specified")))
    reason = escape(str(_value(decision, "reason", "No reason recorded.")))
    action = escape(str(_value(decision, "required_action", "Follow the approved IT workflow.")))
    if label == "CLARIFY":
        action = escape(str(_value(decision, "followup_question", action)))
    st.markdown(
        f"""
        <div class="decision-card {tone}">
          <div class="decision-label">Agent Decision</div>
          <div class="decision-value">{escape(label)}</div>
          <div class="decision-details">
            <div><small>Risk</small><strong>{risk}</strong></div>
            <div><small>Reason</small><strong>{reason}</strong></div>
            <div><small>Action</small><strong>{action}</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_policy_evidence(chunks: list[Any]) -> None:
    with st.expander("POLICY INTELLIGENCE", expanded=False):
        if not chunks:
            st.info("No sufficiently relevant policy evidence found.")
            return
        for index, chunk in enumerate(chunks, start=1):
            citation = escape(str(_value(chunk, "citation", "Policy source")))
            title = escape(str(_value(chunk, "title", "Relevant policy")))
            text = str(_value(chunk, "text", "No excerpt available."))
            st.markdown(f"**{index}. {title}**")
            st.markdown(f'<span class="mono policy-id">{citation}</span>', unsafe_allow_html=True)
            st.write(text)


def _render_history(precedent: list[Any]) -> None:
    with st.expander("HISTORICAL PRECEDENT", expanded=False):
        st.caption("Historical context - not policy")
        if not precedent:
            st.info("No matching historical context available.")
            return
        for ticket in precedent:
            ticket_id = escape(str(_value(ticket, "id", "Historical ticket")))
            issue = escape(str(_value(ticket, "issue", _value(ticket, "description", "Previous IT request"))))
            resolution = escape(str(_value(ticket, "resolution", _value(ticket, "status", "Recorded"))))
            st.markdown(
                f'<div class="precedent-card"><div class="mono">{ticket_id}</div>'
                f'<strong>{issue}</strong><small>Context: {resolution}</small></div>',
                unsafe_allow_html=True,
            )


def _render_trace(state: dict[str, Any]) -> None:
    audit = _value(state, "audit", [])
    if not audit:
        return
    with st.expander("AGENT TRACE", expanded=False):
        st.caption("Technical processing trace for this request.")
        for event in audit:
            event_type = _value(event, "event_type", "Event")
            timestamp = _value(event, "timestamp", "")
            st.markdown(f'<div class="trace-row"><span class="mono">{escape(str(event_type))}</span><small>{escape(str(timestamp))}</small></div>', unsafe_allow_html=True)
    with st.expander("TECHNICAL DETAILS", expanded=False):
        st.json(audit)


def _render_empty_state(title: str, detail: str) -> None:
    st.markdown(
        f'<div class="empty-state"><div class="empty-mark">//</div>'
        f'<strong>{escape(title)}</strong><span>{escape(detail)}</span></div>',
        unsafe_allow_html=True,
    )


def _render_status(label: str, value: str, healthy: bool) -> None:
    state = "status-good" if healthy else "status-muted"
    st.markdown(
        f'<div class="status-item"><span class="status-dot {state}"></span>'
        f'<span><small>{escape(label)}</small><strong>{escape(value)}</strong></span></div>',
        unsafe_allow_html=True,
    )


def _batch_status(request: dict[str, Any], result: dict[str, Any], expected: dict[str, Any] | None) -> str:
    state = result.get("state") or {}
    decision = state.get("decision") or {}
    if not expected:
        return "NEEDS REVIEW"
    actual_status = "escalated" if state.get("ticket") else "followup" if decision.get("needs_followup") else "auto_resolved"
    checks = [
        decision.get("category") == expected.get("expect_category"),
        actual_status == expected.get("expect_status"),
    ]
    if expected.get("expect_escalate_reason"):
        checks.append(decision.get("escalate_reason") == expected["expect_escalate_reason"])
    if expected.get("expect_contains"):
        checks.append(expected["expect_contains"].lower() in str(result.get("response", "")).lower())
    if not all(checks):
        return "FAIL"
    if not state.get("policy_chunks") and decision.get("decision") != "CLARIFY":
        return "NEEDS REVIEW"
    return "PASS"


st.markdown(
    f"""
    <style>
    :root {{ --ink: {"#eaf5fb" if st.session_state.theme_mode == "DARK MODE" else "#17212b"}; --muted: {"#8fa9b8" if st.session_state.theme_mode == "DARK MODE" else "#64727e"}; --line: {"#254458" if st.session_state.theme_mode == "DARK MODE" else "#dce3e8"}; --panel: {"rgba(14, 28, 43, .86)" if st.session_state.theme_mode == "DARK MODE" else "#f7f9fa"}; --card: {"#0e1c2b" if st.session_state.theme_mode == "DARK MODE" else "#ffffff"}; --accent: #59c7e8; --accent-strong: #806dff; --page: {"#08121d" if st.session_state.theme_mode == "DARK MODE" else "#f2f6f8"}; }}
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{ background: var(--page); color: var(--ink); }}
    [data-testid="stHeader"] {{ background: transparent; }}
    .block-container {{ max-width: 1380px; padding-top: 2rem; padding-bottom: 3rem; }}
    [data-testid="stSidebar"] {{ background: {"#0a1724" if st.session_state.theme_mode == "DARK MODE" else "#edf3f6"}; border-right: 1px solid var(--line); }}
    [data-testid="stSidebar"] .block-container {{ padding-top: 1.4rem; }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p, [data-testid="stSidebar"] label {{ color: var(--ink); }}
    [data-testid="stTextInput"] input, [data-testid="stChatInput"] textarea {{ background: var(--card); border-color: var(--line); color: var(--ink); }}
    [data-testid="stTextInput"] input::placeholder, [data-testid="stChatInput"] textarea::placeholder {{ color: var(--muted); }}
    [data-baseweb="select"] > div, [data-baseweb="radio"] {{ background: var(--card); border-color: var(--line); color: var(--ink); }}
    [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {{ background: var(--card); border: 1px solid var(--line); color: var(--ink); }}
    [data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover {{ border-color: var(--accent); color: var(--accent); }}
    .app-header {{ position: relative; border: 1px solid var(--line); border-radius: 10px; background: linear-gradient(110deg, var(--panel), transparent); padding: 1.55rem 1.7rem 1.45rem; margin-bottom: 1rem; overflow: hidden; }}
    .app-header:after {{ content: ""; position: absolute; inset: 0; opacity: .16; pointer-events: none; background-image: linear-gradient(var(--accent) 1px, transparent 1px), linear-gradient(90deg, var(--accent) 1px, transparent 1px); background-size: 32px 32px; mask-image: linear-gradient(110deg, black, transparent 65%); }}
    .app-kicker, .eyebrow {{ color: var(--accent); font-size: .68rem; font-weight: 750; letter-spacing: .16em; text-transform: uppercase; }}
    .brand-line {{ color: var(--ink); font-size: .92rem; font-weight: 750; letter-spacing: .18em; position: relative; z-index: 1; }}
    .brand-line span {{ color: var(--accent-strong); }}
    .app-header h1 {{ color: var(--ink); font-size: 2.15rem; letter-spacing: .04em; line-height: 1.05; margin: .45rem 0 .3rem; position: relative; z-index: 1; }}
    .app-header h1 strong {{ color: var(--accent); font-weight: 780; }}
    .app-header p {{ color: var(--muted); font-size: .98rem; margin: 0 0 .65rem; position: relative; z-index: 1; }}
    .header-status {{ display: flex; flex-wrap: wrap; gap: .85rem 1.2rem; position: relative; z-index: 1; }}
    .header-status span {{ color: var(--muted); font-size: .68rem; letter-spacing: .08em; }}
    .header-status i {{ background: #48c58b; border-radius: 50%; display: inline-block; height: .38rem; margin-right: .35rem; width: .38rem; }}
    .status-strip {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: .75rem 1rem; margin-bottom: 1.15rem; box-shadow: 0 8px 25px rgba(0,0,0,.12); }}
    .status-item {{ display: flex; gap: .55rem; align-items: center; min-height: 2.3rem; }}
    .status-item small, .ticket-grid small, .decision-details small {{ display: block; color: var(--muted); font-size: .68rem; letter-spacing: .06em; margin-bottom: .14rem; text-transform: uppercase; }}
    .status-item strong {{ color: var(--ink); display: block; font-size: .83rem; font-weight: 650; }}
    .status-dot {{ width: .48rem; height: .48rem; border-radius: 50%; display: inline-block; flex: 0 0 auto; box-shadow: 0 0 9px currentColor; }}
    .status-good {{ background: #48c58b; color: #48c58b; }} .status-muted {{ background: #82909a; color: #82909a; }}
    .metric-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: .75rem .9rem; min-height: 4.1rem; }}
    .metric-card small {{ color: var(--muted); display: block; font-size: .65rem; letter-spacing: .11em; text-transform: uppercase; }}
    .metric-card strong {{ color: var(--ink); display: block; font-size: 1.1rem; margin-top: .35rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .decision-card, .ticket-card {{ background: var(--card); border: 1px solid var(--line); border-left: 3px solid var(--accent); border-radius: 8px; padding: 1.05rem 1.15rem; margin: .85rem 0 1rem; box-shadow: 0 0 22px rgba(39, 154, 190, .08); }}
    .glow-border {{ box-shadow: 0 0 24px rgba(89, 199, 232, .1); }}
    .decision-card.resolve {{ border-left-color: #48c58b; }} .decision-card.clarify {{ border-left-color: #e2ad52; }} .decision-card.escalate {{ border-left-color: #ef7373; }}
    .decision-label {{ color: var(--muted); font-size: .68rem; font-weight: 750; letter-spacing: .14em; text-transform: uppercase; }}
    .decision-value {{ color: var(--ink); font-size: 1.35rem; font-weight: 780; letter-spacing: .04em; margin: .25rem 0 .9rem; }}
    .decision-details, .ticket-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .85rem 1.15rem; }}
    .decision-details strong, .ticket-grid strong {{ color: var(--ink); display: block; font-size: .84rem; font-weight: 550; line-height: 1.4; }}
    .ticket-heading {{ display: flex; justify-content: space-between; color: var(--ink); font-weight: 700; margin-bottom: .9rem; }}
    .ticket-status {{ color: #48c58b; font-size: .72rem; font-weight: 750; letter-spacing: .08em; text-transform: uppercase; }}
    .precedent-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 6px; margin: .6rem 0; padding: .7rem .8rem; }}
    .precedent-card strong, .precedent-card small {{ color: var(--ink); display: block; margin-top: .25rem; }} .precedent-card small {{ color: var(--muted); }}
    .trace-row {{ border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; gap: 1rem; padding: .45rem 0; }} .trace-row small {{ color: var(--muted); }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }} .policy-id {{ color: var(--accent); font-size: .75rem; }}
    .section-note {{ color: var(--muted); font-size: .84rem; }} .empty-state {{ background: var(--panel); border: 1px dashed var(--line); border-radius: 8px; margin: 1rem 0; padding: 2rem; text-align: center; }} .empty-state strong, .empty-state span {{ display: block; }} .empty-state strong {{ color: var(--ink); margin: .4rem 0; }} .empty-state span {{ color: var(--muted); font-size: .85rem; }} .empty-mark {{ color: var(--accent); font-family: monospace; font-weight: 700; }}
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{ color: var(--ink); }}
    [data-testid="stDataFrame"] {{ border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
    [data-testid="stDataFrame"] iframe {{ background: var(--card); }}
    [data-baseweb="tab-list"] {{ border-bottom: 1px solid var(--line); gap: .25rem; }} [data-baseweb="tab"] {{ color: var(--muted); }} [aria-selected="true"] {{ color: var(--accent) !important; }}
    [data-testid="stExpander"] {{ background: var(--panel); border-color: var(--line); }} [data-testid="stExpander"] summary {{ color: var(--ink); }}
    [data-testid="stChatMessage"] {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; margin-bottom: .7rem; }}
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {{ color: var(--ink); }}
    button {{ border-radius: 6px !important; }}
    @media (max-width: 800px) {{ .decision-details, .ticket-grid {{ grid-template-columns: 1fr; }} .app-header h1 {{ font-size: 1.55rem; }} .header-status {{ gap: .5rem .8rem; }} }}
    </style>
    """,
    unsafe_allow_html=True,
)


if st.session_state.pending_batch:
    _run_batch()
_process_pending_submission()

health = _health_checks()
health_ok = all(health.values())

st.markdown(
    f"""
    <header class="app-header">
            <div class="brand-line">VERIDIAN <span>//</span> INTERNAL IT</div>
            <h1>IT SERVICE <strong>INTELLIGENCE</strong></h1>
      <p>Policy-Grounded Internal Employee Support</p>
            <div class="header-status">
                <span><i></i>AGENT {"ONLINE" if agent is not None else "UNAVAILABLE"}</span>
                <span><i></i>POLICY KB {"READY" if health["policy"] else "CHECK REQUIRED"}</span>
                <span><i></i>AUDIT {"ENABLED" if health["audit"] else "CHECK REQUIRED"}</span>
            </div>
    </header>
    """,
    unsafe_allow_html=True,
)

status_columns = st.columns(4)
status_values = [
    ("Agent", "Ready", agent is not None),
    ("Policy KB", "Available", health["policy"] and bool(getattr(getattr(agent, "policy_retriever", None), "chunks", []))),
    ("Ticketing", "Enabled", health["tickets"] and callable(getattr(agent, "handle", None))),
    ("Audit", "Enabled", health["audit"] and callable(getattr(getattr(agent, "audit", None), "log", None))),
]
with st.container():
    st.markdown('<div class="status-strip">', unsafe_allow_html=True)
    for column, (label, value, healthy) in zip(status_columns, status_values):
        with column:
            _render_status(label, value if healthy else "Unavailable", healthy)
    st.markdown("</div>", unsafe_allow_html=True)

latest_state: dict[str, Any] = {}
for stored_message in reversed(st.session_state.messages):
    if stored_message.get("role") == "assistant" and stored_message.get("result"):
        latest_state = stored_message["result"].get("state") or {}
        break
active_request = "NO ACTIVE REQUEST"
for stored_message in reversed(st.session_state.messages):
    if stored_message.get("role") == "user":
        active_request = stored_message.get("content", "NO ACTIVE REQUEST")
        break
latest_decision = _value(latest_state, "decision", {})
policy_sources = _value(latest_decision, "policy_sources", [])
session_tickets = sum(
    1
    for stored_message in st.session_state.messages
    if _value(_value(stored_message.get("result", {}), "state", {}), "ticket", None)
)
metric_columns = st.columns(4)
metric_values = [
    ("ACTIVE REQUEST", active_request),
    ("POLICY SOURCES", len(policy_sources) if isinstance(policy_sources, list) else 0),
    ("AUDIT EVENTS", agent.audit.events),
    ("TICKETS", session_tickets),
]
for column, (label, value) in zip(metric_columns, metric_values):
    with column:
        st.markdown(
            f'<div class="metric-card"><small>{escape(label)}</small><strong>{escape(str(value))}</strong></div>',
            unsafe_allow_html=True,
        )

with st.sidebar:
    st.markdown("### SESSION")
    st.caption("Employee context for the active conversation.")
    st.caption("Load a prepared request or start a free-form conversation.")
    employee = st.text_input("Employee name", "Demo Employee")
    employee_email = st.text_input("Employee email", "")
    employee_id = st.text_input("Employee ID", "EMP-001")
    st.markdown("### DEMO CONTROL")
    request_ids = [item.get("id") for item in requests if item.get("id")]
    selected = st.selectbox("Load official request", ["None"] + request_ids, key="official_request_id")
    if selected != "None" and st.button("Use selected request"):
        request = next((item for item in requests if item.get("id") == selected), None)
        if request and isinstance(request.get("text"), str):
            _queue_submission(
                request["text"],
                {
                    "name": request.get("employee", employee),
                    "email": employee_email,
                    "employee_id": request.get("id", employee_id),
                },
            )
            st.rerun()
    if st.button("New conversation"):
        st.session_state.messages = []
        st.session_state.pending_submission = None
        st.session_state.pending_batch = False
        st.session_state.batch_rows = None
        agent.reset()
        st.rerun()
    st.divider()
    st.markdown("### SYSTEM")
    st.caption("SYSTEM HEALTH: HEALTHY" if health_ok else "SYSTEM HEALTH: CHECK REQUIRED")
    st.caption("Agent: Ready" if agent is not None else "Agent: Unavailable")
    st.caption("Policy knowledge base: Available" if status_values[1][2] else "Policy knowledge base: Unavailable")
    st.caption("Ticketing: Enabled" if status_values[2][2] else "Ticketing: Unavailable")
    st.caption("Audit: Enabled" if status_values[3][2] else "Audit: Unavailable")
    st.caption(f"Audit events recorded: {agent.audit.events}")
    st.markdown("### APPEARANCE")
    st.radio("Interface theme", ["DARK MODE", "LIGHT MODE"], key="theme_mode", label_visibility="collapsed", horizontal=True)

chat_tab, batch_tab, queue_tab, audit_tab, about_tab = st.tabs(["Chat", "Batch QA", "Ticket Queue", "Audit Trail", "Architecture / About"])
with chat_tab:
    st.markdown("### EMPLOYEE REQUEST")
    st.markdown('<p class="section-note">Describe an IT issue or load an official request to begin an auditable support workflow.</p>', unsafe_allow_html=True)
    if not st.session_state.messages:
        _render_empty_state("NO ACTIVE REQUEST", "Select an official request or enter an employee issue to begin.")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            message_state = _value(message.get("result", {}), "state", {})
            message_decision = _value(message_state, "decision", {})
            if message["role"] == "user":
                st.caption("EMPLOYEE")
            elif _value(message_decision, "decision", "") == "CLARIFY":
                st.caption("AGENT / FOLLOW-UP")
            else:
                st.caption("AGENT")
            st.markdown(message["content"])
            if message.get("result"):
                state = message["result"].get("state") or {}
                decision = state.get("decision") or {}
                _render_decision(state)
                _render_policy_evidence(state.get("policy_chunks", []))
                _render_history(state.get("precedent", []))
                _render_trace(state)
                if state.get("ticket"):
                    _render_ticket(state["ticket"])
    prompt = st.chat_input("Describe your IT issue...", key="chat_input")
    if prompt:
        _queue_submission(prompt, {"name": employee, "email": employee_email, "employee_id": employee_id})
        st.rerun()

with batch_tab:
    st.markdown("### BATCH RUN / OFFICIAL REQUESTS")
    st.markdown('<p class="section-note">Run the prepared request set through the same policy, decision, and ticketing workflow.</p>', unsafe_allow_html=True)
    if st.button("Run all 15 requests"):
        st.session_state.pending_batch = True
        st.rerun()
    if st.session_state.get("batch_rows"):
        batch_rows = st.session_state.batch_rows
        batch_counts = {status: sum(row.get("Decision") == status for row in batch_rows) for status in ("RESOLVE", "CLARIFY", "ESCALATE")}
        qa_counts = {status: sum(row.get("Status") == status for row in batch_rows) for status in ("PASS", "NEEDS REVIEW", "FAIL")}
        batch_metrics = st.columns(3)
        for column, status in zip(batch_metrics, ("PASS", "NEEDS REVIEW", "FAIL")):
            with column:
                st.metric(status, qa_counts[status])
        st.caption(f"Decision mix: RESOLVE {batch_counts['RESOLVE']} / CLARIFY {batch_counts['CLARIFY']} / ESCALATE {batch_counts['ESCALATE']}")
        st.dataframe(st.session_state.batch_rows, use_container_width=True)
        st.download_button("Download results", json.dumps(st.session_state.batch_rows, indent=2), "batch_results.json", "application/json")

with queue_tab:
    st.markdown("### TICKET QUEUE")
    st.markdown('<p class="section-note">Historical tickets are precedent and context, not policy. Generated service tickets are stored separately.</p>', unsafe_allow_html=True)
    tickets = _load_json("data/tickets/ticket_queue.json")
    ticket_rows = [
        {
            "Ticket": ticket.get("id", ""),
            "Employee": ticket.get("employee", ""),
            "Issue": ticket.get("issue", ""),
            "Status": ticket.get("status", "Recorded"),
            "Precedent": "Indexed",
        }
        for ticket in tickets
    ]
    closed_rows = [row for row in ticket_rows if "closed" in str(row["Status"]).lower() or "resolved" in str(row["Status"]).lower()]
    active_rows = [row for row in ticket_rows if row not in closed_rows]
    st.markdown("#### Open / Active")
    st.dataframe(active_rows, use_container_width=True, hide_index=True)
    st.markdown("#### Closed / History")
    st.dataframe(closed_rows, use_container_width=True, hide_index=True)
    if agent.last_ticket:
        st.markdown("#### Latest generated service ticket")
        _render_ticket(agent.last_ticket)

with audit_tab:
    st.markdown("### AUDIT TRAIL")
    st.markdown('<p class="section-note">Append-only meaningful events from the agent workflow. Streamlit rendering does not create audit events.</p>', unsafe_allow_html=True)
    audit_rows = _load_audit_rows()
    st.metric("Total meaningful audit events", len(audit_rows))
    if audit_rows:
        st.dataframe(audit_rows[-100:], use_container_width=True, hide_index=True)
    else:
        _render_empty_state("NO AUDIT EVENTS", "Audit events will appear here after the first request is processed.")
    if agent.last_ticket:
        with st.expander("Latest ticket technical details", expanded=False):
            st.json(agent.last_ticket)

with about_tab:
    st.markdown("### ARCHITECTURE / ABOUT")
    st.markdown('<p class="section-note">Deterministic, offline-first orchestration for reproducible policy-grounded support decisions.</p>', unsafe_allow_html=True)
    st.code("""Employee Request
    -> Observe / Classify
    -> Policy Search + Historical Precedent
    -> Risk Assessment
    -> RESOLVE / CLARIFY / ESCALATE
    -> Action or Structured Ticket
    -> Append-only Audit Trail
    -> Streamlit UI""", language="text")
    st.markdown("#### System boundaries")
    st.write("Policy evidence comes from the local Veridian KB. Historical tickets are retrieved separately as precedent. Actions and ticket creation are deterministic local simulations; no external LLM or API key is required.")
    st.markdown("#### Current health")
    st.write("Policy file: " + ("available" if health["policy"] else "unavailable"))
    st.write("Ticket store: " + ("readable" if health["tickets"] else "unavailable"))
    st.write("Audit store: " + ("writable" if health["audit"] else "unavailable"))



