# app.py - CareerPilot AI v3
# FIXED: All tabs work, no rerun bugs, Windows compatible
# Lemma pod-aware: work lands in tables and files, not just chat

import streamlit as st
import pdfplumber
import json
from copy import deepcopy
from datetime import datetime, date, timedelta

from database import (
  init_db, reset_workspace, save_resume, get_resume,
  save_application, get_all_applications,
  update_application, delete_application, application_exists,
  save_market_skills, get_market_skills, get_all_role_categories,
  save_interview_session, get_interview_sessions, get_interview_avg_scores,
  save_employability, get_employability,
  log_workflow, get_workflow_logs,
  get_analytics
)
from agents import (
  set_api_key, get_runtime_status, resume_agent, jd_agent,
  matching_agent, market_agent, message_agent,
  interview_question_agent, interview_evaluate_agent,
  employability_agent, resume_optimizer_agent,
  OrchestrationAgent
)

# ── MUST BE FIRST ─────────────────────────────────────────────────────────────
st.set_page_config(
  page_title="CareerPilot AI",
  page_icon=None,
  layout="wide",
  initial_sidebar_state="expanded"
)
init_db()


st.markdown("""
<style>
  :root {
    --cp-bg: #F4F6F8;
    --cp-panel: #FFFFFF;
    --cp-panel-soft: #F8FAFC;
    --cp-border: #D7DEE5;
    --cp-text: #111827;
    --cp-muted: #5B6673;
    --cp-sidebar: #0B1220;
    --cp-sidebar-soft: #111A2E;
    --cp-sidebar-border: #23314D;
    --cp-teal: #0F766E;
    --cp-teal-soft: #E6F4F1;
    --cp-blue-soft: #EAF2FF;
    --cp-red: #A33A3A;
  }

  .stApp,
  [data-testid="stAppViewContainer"] {
    background: var(--cp-bg) !important;
    color: var(--cp-text) !important;
  }

  [data-testid="stHeader"] {
    background: rgba(244, 246, 248, 0.92) !important;
    backdrop-filter: blur(8px);
    border-bottom: 1px solid rgba(215, 222, 229, 0.75);
  }

  .block-container {
    padding: 1.4rem 2.25rem 3rem !important;
    max-width: 1320px !important;
    margin: 0 auto !important;
  }

  section[data-testid="stSidebar"] {
    background: var(--cp-sidebar) !important;
    border-right: 1px solid var(--cp-sidebar-border) !important;
  }

  section[data-testid="stSidebar"] {
    min-width: 292px !important;
    max-width: 292px !important;
  }

  section[data-testid="stSidebar"] > div {
    width: 292px !important;
  }

  section[data-testid="stSidebar"] h2 {
    font-size: 25px !important;
    line-height: 1.15 !important;
    white-space: nowrap !important;
  }

  section[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
    background: #FFFFFF !important;
    color: #111827 !important;
    border: 1px solid #CBD5E1 !important;
  }

  section[data-testid="stSidebar"] [data-testid="stFileUploader"] small,
  section[data-testid="stSidebar"] [data-testid="stFileUploader"] span,
  section[data-testid="stSidebar"] [data-testid="stFileUploader"] p {
    color: #D8DEE9 !important;
  }


  section[data-testid="stSidebar"] * {
    color: #E5EAF2 !important;
  }

  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
  section[data-testid="stSidebar"] small,
  section[data-testid="stSidebar"] label {
    color: #AEB8C8 !important;
  }

  section[data-testid="stSidebar"] h1,
  section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3,
  section[data-testid="stSidebar"] strong {
    color: #FFFFFF !important;
  }

  section[data-testid="stSidebar"] hr {
    border-color: var(--cp-sidebar-border) !important;
  }

  section[data-testid="stSidebar"] input {
    background: #FFFFFF !important;
    color: #111827 !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
  }

  section[data-testid="stSidebar"] input::placeholder {
    color: #64748B !important;
  }

  section[data-testid="stSidebar"] [data-testid="stAlert"] {
    background: var(--cp-sidebar-soft) !important;
    border: 1px solid var(--cp-sidebar-border) !important;
  }

  section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: var(--cp-sidebar-soft) !important;
    border: 1px solid var(--cp-sidebar-border) !important;
    border-radius: 8px !important;
    padding: 0.65rem !important;
  }

  .cp-topbar {
    background: var(--cp-panel);
    border: 1px solid var(--cp-border);
    border-radius: 8px;
    padding: 18px 22px;
    margin: 0 0 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
  }

  .cp-title {
    font-size: 27px;
    font-weight: 750;
    line-height: 1.1;
    color: var(--cp-text);
  }

  .cp-subtitle {
    margin-top: 6px;
    color: var(--cp-muted);
    font-size: 14px;
  }

  .cp-status {
    border: 1px solid #BFD7D2;
    background: var(--cp-teal-soft);
    border-radius: 999px;
    padding: 9px 14px;
    color: #115E59;
    font-weight: 700;
    font-size: 13px;
    white-space: nowrap;
  }

  div[data-testid="stTabs"] [role="tablist"] {
    background: var(--cp-panel);
    border: 1px solid var(--cp-border);
    border-radius: 8px;
    padding: 6px;
    gap: 4px;
    margin-bottom: 18px;
  }

  div[data-testid="stTabs"] button[role="tab"] {
    border-radius: 7px !important;
    padding: 9px 14px !important;
    color: var(--cp-muted) !important;
    font-weight: 700 !important;
  }

  div[data-testid="stTabs"] button[aria-selected="true"] {
    background: var(--cp-teal-soft) !important;
    color: #115E59 !important;
  }

  h1, h2, h3,
  [data-testid="stMarkdownContainer"] h1,
  [data-testid="stMarkdownContainer"] h2,
  [data-testid="stMarkdownContainer"] h3 {
    color: var(--cp-text) !important;
    letter-spacing: 0 !important;
  }

  h2, [data-testid="stMarkdownContainer"] h2 {
    font-size: 34px !important;
    line-height: 1.15 !important;
    margin-bottom: 0.85rem !important;
  }

  h3, [data-testid="stMarkdownContainer"] h3 {
    font-size: 21px !important;
    line-height: 1.25 !important;
  }

  p, li, label, span, div[data-testid="stMarkdownContainer"] {
    color: var(--cp-text);
  }

  div[data-testid="stMetric"] {
    background: var(--cp-panel) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 8px !important;
    padding: 16px 18px !important;
    min-height: 104px !important;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06) !important;
  }

  div[data-testid="stMetric"] * {
    color: var(--cp-text) !important;
  }

  div[data-testid="stMetricLabel"] p {
    color: var(--cp-muted) !important;
    font-weight: 700 !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    line-height: 1.25 !important;
    font-size: 13px !important;
  }

  div[data-testid="stMetricValue"] {
    color: var(--cp-text) !important;
    font-size: 28px !important;
    font-weight: 750 !important;
  }

  .stButton > button {
    border-radius: 8px !important;
    font-weight: 750 !important;
    min-height: 42px !important;
    border: 1px solid var(--cp-border) !important;
    background: #FFFFFF !important;
    color: var(--cp-text) !important;
  }

  .stButton > button[kind="primary"] {
    background: var(--cp-teal) !important;
    border-color: var(--cp-teal) !important;
    color: #FFFFFF !important;
  }

  .stTextInput input,
  .stTextArea textarea {
    border-radius: 8px !important;
    border: 1px solid var(--cp-border) !important;
    background: #FFFFFF !important;
    color: var(--cp-text) !important;
  }

  .stTextArea textarea {
    min-height: 220px;
  }

  div[data-testid="stExpander"],
  div[data-testid="stAlert"] {
    border-radius: 8px !important;
    border: 1px solid var(--cp-border) !important;
  }

  .cp-pill {
    border-radius: 999px;
    font-size: 12px;
    font-weight: 750;
    display: inline-block;
    margin: 3px 4px 3px 0;
    padding: 5px 10px;
    border: 1px solid transparent;
  }

  @media (max-width: 980px) {
    .block-container {
      padding-left: 1rem !important;
      padding-right: 1rem !important;
    }
    .cp-topbar {
      align-items: flex-start;
      flex-direction: column;
    }
    .cp-title {
      font-size: 23px;
    }
  }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE (all keys defined once, safely) ─────────────────────────────
_DEFAULTS = {
  "api_key_set":    False,
  "resume_profile":  {},
  "last_analysis":   None,
  "bulk_results":   [],
  "market_data":    {},
  "career_result":   None,
  "int_active":    False,
  "int_question":   "",
  "int_round":     1,
  "int_company":    "",
  "int_role":     "",
  "int_missing":    [],
  "int_scores":    [],
  "delete_confirm":  None,
}
for k, v in _DEFAULTS.items():
  if k not in st.session_state:
    st.session_state[k] = deepcopy(v)

# Fresh browser sessions should start clean for hackathon demos.
# Normal widget interactions rerun Streamlit but keep this flag, so user actions are not wiped.
if "fresh_session_reset_done" not in st.session_state:
  reset_workspace()
  for key, value in _DEFAULTS.items():
    st.session_state[key] = deepcopy(value)
  st.session_state.fresh_session_reset_done = True

# ── HELPER FUNCTIONS ──────────────────────────────────────────────────────────
def score_icon(s):
  return "High" if s >= 75 else "Medium" if s >= 50 else "Low"

def pill(text, bg, color):
  return (
    f'<span class="cp-pill" style="background:{bg};color:{color};border-color:{bg}">'
    f'{text}</span>'
  )

def action_banner(action, message):
  cfg = {
    "IMMEDIATE_APPLY":  ("success", ""),
    "APPLY_WITH_TAILORING": ("warning", ""),
    "UPSKILL_FIRST":   ("error",  ""),
  }
  box, icon = cfg.get(action, ("info", ""))
  getattr(st, box)(message)

def progress_bar_html(label, count, total, color):
  pct = int((count/total)*100) if total else 0
  return (
    f'<div style="margin-bottom:10px">'
    f'<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:3px">'
    f'<span>{label}</span><span style="font-weight:500">{count} ({pct}%)</span></div>'
    f'<div style="background:#e8e6de;border-radius:4px;height:10px">'
    f'<div style="background:{color};width:{pct}%;height:10px;border-radius:4px"></div>'
    f'</div></div>'
  )


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
  st.markdown("## CareerPilot AI")
  st.caption("Agentic Job Application Platform")
  st.divider()

  # API KEY
  st.markdown("**AI Runtime Key**")
  api_key_input = st.text_input(
    "key", type="password", placeholder="Lemma/Lemme or OpenAI key",
    label_visibility="collapsed",
    help="Use a Lemma/Lemme key when available, or an OpenAI key. Stored only for this session."
  )
  if api_key_input:
    if not st.session_state.api_key_set:
      set_api_key(api_key_input)
      st.session_state.api_key_set = True
    st.success(f"AI active: {get_runtime_status()['runtime']}")
  else:
    st.info("No key - universal demo mode")

  st.divider()

  # RESUME UPLOAD
  st.markdown("**Your Resume**")
  uploaded = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")

  if uploaded is not None:
    with pdfplumber.open(uploaded) as pdf:
      resume_text_new = "".join(p.extract_text() or "" for p in pdf.pages)

    if len(resume_text_new.strip()) < 50:
      st.error("Could not read this PDF. Try saving it as a plain PDF (not scanned).")
    else:
      save_resume(resume_text_new, uploaded.name)
      with st.spinner("Parsing resume..."):
        profile = resume_agent(resume_text_new)
        st.session_state.resume_profile = profile
      st.success(f"Uploaded: {uploaded.name}")
      if profile.get("name","Unknown") != "Unknown":
        st.caption(f"Profile: {profile['name']}")
      if profile.get("top_skills"):
        st.caption("Skills: " + ", ".join(profile["top_skills"][:3]))

  # Load from DB if already uploaded
  resume_text = get_resume()
  if resume_text and uploaded is None:
    st.info("Resume loaded from DB")
    if not st.session_state.resume_profile:
      st.session_state.resume_profile = resume_agent(resume_text)

  st.divider()

  # Quick stats
  stats = get_analytics()
  emp  = get_employability()
  emp_score = emp.get("overall_score", stats.get("employability", 0))
  st.markdown(f"**Apps:** {stats['total']} **Interviews:** {stats['interview']}")
  st.markdown(f"**Employability:** {emp_score}%")
  st.divider()
  st.caption("Lemma Pod: pod/")
  st.caption("Gappy AI Hackathon 2026")
  st.divider()
  if st.button("Reset Demo", use_container_width=True, help="Clear resume, applications, interview history, workflow logs, and cached analysis"):
    reset_workspace()
    for key, value in _DEFAULTS.items():
      st.session_state[key] = deepcopy(value)
    st.success("Demo workspace reset")
    st.rerun()


# ── TABS ──────────────────────────────────────────────────────────────────────
runtime = get_runtime_status()
runtime_label = runtime.get("runtime", "demo").title()
st.markdown(f"""
<div class="cp-topbar">
  <div>
    <div class="cp-title">CareerPilot AI</div>
    <div class="cp-subtitle">Universal job matching, application tracking, interview practice, and Lemma-style workflow logs.</div>
  </div>
  <div class="cp-status">Runtime: {runtime_label}</div>
</div>
""", unsafe_allow_html=True)

tab_dashboard, tab_analyser, tab_bulk, tab_tracker, \
tab_market, tab_messages, tab_interview, tab_workflow = st.tabs([
  "Dashboard",
  "JD Analyser",
  "Bulk Ranker",
  "Tracker",
  "Market Intel",
  "Messages",
  "Interview Sim",
  "Workflow"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 - DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_dashboard:
  stats = get_analytics()
  emp  = get_employability()

  st.markdown("## Career Dashboard")

  if stats["total"] == 0:
    st.info("Get started: upload your resume - analyse a JD - your dashboard fills in automatically.")
    st.markdown("""
**Quick start guide:**
1. Upload resume PDF in the left sidebar
2. Add your OpenAI API key (or use demo mode)
3. **JD Analyser tab** - paste any job description - click Analyse
4. **Bulk Ranker tab** - paste multiple JDs - get priority queue
5. **Market Intel tab** - upload 10+ JDs - see skill frequency
6. **Interview Sim tab** - practice before real interviews
    """)
  else:
    # KPI row
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("Total Applied", stats["total"])
    k2.metric("Screening",   stats["screening"])
    k3.metric("Interviews",   stats["interview"])
    k4.metric("Offers",     stats["offer"])
    k5.metric("Avg Fit Score", f"{stats['avg_fit']}%")
    k6.metric("Employability", f"{emp.get('overall_score', stats['employability'])}%")

    st.divider()

    col_left, col_mid, col_right = st.columns([2,1,1])

    with col_left:
      st.markdown("### Application Funnel")
      total = stats["total"] or 1
      for label, count, color in [
        ("Applied",  stats["applied"],  "#1D9E75"),
        ("Screening", stats["screening"], "#185FA5"),
        ("Interview", stats["interview"], "#BA7517"),
        ("Offer",   stats["offer"],   "#639922"),
        ("Rejected", stats["rejected"], "#A32D2D"),
      ]:
        st.markdown(progress_bar_html(label, count, total, color), unsafe_allow_html=True)

    with col_mid:
      st.markdown("### Fit Distribution")
      dist = stats.get("fit_distribution", [])
      max_d = max((c for _,c in dist), default=1) or 1
      for label, count in dist:
        bar = int((count/max_d)*100)
        st.markdown(
          f'<div style="margin-bottom:8px">'
          f'<div style="font-size:12px;margin-bottom:2px">{label}: {count}</div>'
          f'<div style="background:#e8e6de;border-radius:3px;height:7px">'
          f'<div style="background:#1D9E75;width:{bar}%;height:7px;border-radius:3px"></div>'
          f'</div></div>',
          unsafe_allow_html=True
        )

    with col_right:
      st.markdown("### Top Skill Gaps")
      top_miss = stats.get("top_missing_skills", [])
      if top_miss:
        max_m = max(c for _,c in top_miss) or 1
        for skill, count in top_miss[:6]:
          bar = int((count/max_m)*100)
          st.markdown(
            f'<div style="margin-bottom:8px">'
            f'<div style="font-size:12px;margin-bottom:2px">{skill} ({count}x)</div>'
            f'<div style="background:#e8e6de;border-radius:3px;height:7px">'
            f'<div style="background:#A32D2D;width:{bar}%;height:7px;border-radius:3px"></div>'
            f'</div></div>',
            unsafe_allow_html=True
          )

    st.divider()

    # Employability breakdown
    if emp:
      st.markdown("### Employability Score")
      e1,e2,e3,e4,e5 = st.columns(5)
      e1.metric("Overall",    f"{emp.get('overall_score',0)}%")
      e2.metric("Resume",    f"{emp.get('resume_score',0)}%")
      e3.metric("Skill Match",  f"{emp.get('skill_match_score',0)}%")
      e4.metric("Market Demand", f"{emp.get('market_demand_score',0)}%")
      e5.metric("App Success",  f"{emp.get('application_score',0)}%")
      recs = emp.get("top_recommendations", [])
      if recs:
        st.markdown("**Learning roadmap:**")
        for r in recs[:3]:
          ca, cb = st.columns([3,1])
          ca.markdown(f"- **{r['action']}** - {r.get('reason','')}")
          cb.markdown(f"+{r['impact']}% - {r['time_weeks']}w")

    # Role category breakdown
    cats = stats.get("role_categories", [])
    if len(cats) > 1:
      st.divider()
      st.markdown("### Applications by Role Category")
      cat_cols = st.columns(min(len(cats), 4))
      for i, (cat, cnt) in enumerate(cats[:4]):
        cat_cols[i].metric(cat, cnt)

    # Follow-up queue
    st.divider()
    apps_all = get_all_applications()
    today  = date.today().isoformat()
    fups = [
      a for a in apps_all
      if a["status"] in ["Applied","Screening"]
      and a.get("follow_up_date","9999") <= today
    ]
    if fups:
      st.markdown("### Follow Up Today")
      for a in fups[:5]:
        st.markdown(
          f"- **{a['company']}** - {a['role']} "
          f"{score_icon(a['fit_score'])} {a['fit_score']}% "
          f"- Applied {a['date_applied']}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 - JD ANALYSER
# FIXED: No nested st.rerun(), works for ANY role type
# ══════════════════════════════════════════════════════════════════════════════
with tab_analyser:
  st.markdown("## JD Analyser")
  st.caption("Works for any role - Data Science, Engineering, Product, Marketing, Finance, and more")

  resume_text = get_resume()
  if not resume_text:
    st.warning("Upload your resume in the sidebar first")

  col_jd, col_meta = st.columns([1.3, 0.7], gap="large")

  with col_jd:
    jd_input = st.text_area(
      "Paste the full job description",
      height=300,
      placeholder="Paste any job description here - from LinkedIn, Naukri, company websites...\n\nWorks for ALL roles: Data Science, Software Engineering, Product, Marketing, Sales, Finance, HR, Design, Operations, and more.",
      key="jd_input_text"
    )

  with col_meta:
    st.markdown("**Company & Role** *(optional - auto-detected from JD)*")
    company_input = st.text_input(
      "Company name",
      placeholder="e.g. YesMadam, Infosys, Swiggy",
      key="jd_company"
    )
    role_input = st.text_input(
      "Role title",
      placeholder="e.g. Data Analyst, Product Manager, Software Engineer",
      key="jd_role"
    )
    st.markdown(" ")
    with st.expander("Tips for best results"):
      st.markdown("""
- Paste the **full** JD including the requirements section
- Fit score > 75% = apply immediately
- ATS score = how well your resume passes keyword filters
- Skill gap % = fit improvement if you add that skill
- Role category is auto-detected - works for any field
""")

  analyse_disabled = not (resume_text and jd_input.strip())
  if st.button("Analyse My Fit", type="primary",
         use_container_width=True, disabled=analyse_disabled):

    orch = OrchestrationAgent()
    prog = st.progress(0)
    stat = st.empty()

    def _prog(msg, n, total):
      prog.progress(n/total)
      stat.caption(msg)

    with st.spinner(""):
      result = orch.run_single_analysis(
        resume_text, jd_input,
        company_input, role_input,
        progress_fn=_prog
      )

    prog.empty()
    stat.empty()
    st.session_state.last_analysis = result
    st.success("Analysis complete!")

  # RESULTS - shown from session state, no rerun needed
  r = st.session_state.last_analysis
  if r:
    st.divider()

    # Workflow action banner
    action_banner(r.get("workflow_action",""), r.get("workflow_message",""))

    # Role category badge
    cat = r.get("role_category","General")
    st.markdown(
      pill(f"Role Category: {cat}", "#E6F1FB", "#0C447C"),
      unsafe_allow_html=True
    )
    st.markdown(" ")

    # Score metrics
    fit = int(r.get("fit_score",0))
    ats = int(r.get("ats_score",0))
    opp = int(r.get("opportunity_score",0))

    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Fit Score",    f"{score_icon(fit)} {fit}/100")
    m2.metric("ATS Score",    f"{score_icon(ats)} {ats}/100")
    m3.metric("Opportunity",   f"{opp}/100")
    m4.metric("Matched Skills", len(r.get("matched_skills",[])))
    m5.metric("Missing Skills", len(r.get("missing_skills",[])))

    st.info(f"**Verdict:** {r.get('one_line_verdict','')}")

    # Skills
    sk1, sk2 = st.columns(2)
    with sk1:
      st.markdown("**Skills You Have**")
      matched = r.get("matched_skills",[])
      if matched:
        html = " ".join(pill(s,"#E1F5EE","#085041") for s in matched)
        st.markdown(html, unsafe_allow_html=True)
      else:
        st.caption("No matching skills detected")

    with sk2:
      st.markdown("**Skill Gaps**")
      missing = r.get("missing_skills",[])
      gap   = r.get("skill_gap_impact",{})
      if missing:
        html = " ".join(
          pill(f"{s} +{gap[s]}%" if s in gap else s, "#FCEBEB", "#791F1F")
          for s in missing
        )
        st.markdown(html, unsafe_allow_html=True)
        if gap:
          st.caption("% = fit score improvement if you learn that skill")
      else:
        st.caption("No skill gaps detected")

    # Resume suggestions
    suggestions = r.get("resume_suggestions",[])
    if suggestions:
      st.markdown("**Resume Suggestions for This Role**")
      for i, s in enumerate(suggestions, 1):
        st.markdown(f"**{i}.** {s}")

    # Cover note
    if r.get("cover_note"):
      with st.expander("AI-Generated Cover Note"):
        st.markdown(r["cover_note"])
        st.caption("Edit and personalise before using")

    st.divider()

    # Save to tracker
    save_col, _ = st.columns([1.2, 2])
    with save_col:
      if st.button("Save to Application Tracker", type="secondary"):
        res = save_application(r)
        if res > 0:
          st.success(f"Saved! {r.get('company','')} - {r.get('role','')} added to tracker.")
        elif res == -1:
          st.warning("Already in tracker")
        else:
          st.error("Could not save - check logs")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 - BULK RANKER
# FIXED: Proper progress, no tab interference
# ══════════════════════════════════════════════════════════════════════════════
with tab_bulk:
  st.markdown("## Bulk JD Ranker")
  st.caption("Paste 2-20 JDs of ANY type - get ranked by opportunity score - know where to apply first")

  resume_text = get_resume()
  if not resume_text:
    st.warning("Upload your resume first")

  bulk_input = st.text_area(
    "Paste job descriptions - separate each with ---",
    height=300,
    placeholder="[JD 1] Paste first job description here...\n---\n[JD 2] Paste second job description here...\n---\n[JD 3] And so on...\n\nTip: Mix different role types freely - each is analysed independently.",
    key="bulk_jd_input"
  )

  if st.button("Rank All Opportunities", type="primary",
         disabled=not (resume_text and bulk_input.strip())):

    jd_list = [j.strip() for j in bulk_input.split("---") if len(j.strip()) > 50]

    if len(jd_list) < 2:
      st.error("Add at least 2 job descriptions separated by ---")
    else:
      prog = st.progress(0)
      stat = st.empty()

      def _bulk_prog(current, total, msg):
        prog.progress(current/total)
        stat.caption(msg)

      orch = OrchestrationAgent()
      with st.spinner(""):
        ranked = orch.run_bulk_analysis(resume_text, jd_list, _bulk_prog)

      prog.empty()
      stat.empty()
      st.session_state.bulk_results = ranked
      st.success(f"Ranked {len(ranked)} opportunities!")

  # Show results
  ranked = st.session_state.bulk_results
  if ranked:
    st.divider()
    st.markdown(f"### Priority Queue - {len(ranked)} Opportunities")

    # Summary table
    action_labels = {
      "IMMEDIATE_APPLY":  " Apply Now",
      "APPLY_WITH_TAILORING": " Tailor First",
      "UPSKILL_FIRST":   " Upskill"
    }
    header = "Rank | Company | Role | Category | Fit | ATS | Score | Action"
    rows  = []
    for i, r in enumerate(ranked):
      rows.append(
        f"#{i+1} | **{r.get('company','?')}** | {r.get('role','?')} | "
        f"{r.get('role_category','?')} | {r.get('fit_score',0)}% | "
        f"{r.get('ats_score',0)}% | {r.get('opportunity_score',0)} | "
        f"{action_labels.get(r.get('workflow_action',''),'-')}"
      )

    # HTML table
    th = "".join(f'<th style="padding:8px 10px;background:#0F6E56;color:white;font-size:12px;text-align:left">{h}</th>'
           for h in ["#","Company","Role","Category","Fit","ATS","Score","Action"])
    trs = ""
    for i, r in enumerate(ranked):
      bg  = "#F5F4F0" if i%2==0 else "#FFFFFF"
      medal = f"#{i+1}"
      vals = [
        medal,
        r.get("company","?"),
        r.get("role","?"),
        r.get("role_category","General"),
        f"{r.get('fit_score',0)}%",
        f"{r.get('ats_score',0)}%",
        str(r.get("opportunity_score",0)),
        action_labels.get(r.get("workflow_action",""),"-")
      ]
      trs += f'<tr style="background:{bg}">' + "".join(
        f'<td style="padding:7px 10px;font-size:12px">{v}</td>' for v in vals
      ) + "</tr>"

    st.markdown(
      f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse">'
      f'<tr>{th}</tr>{trs}</table></div>',
      unsafe_allow_html=True
    )
    st.divider()

    # Detailed expandable cards
    st.markdown("### Detailed Breakdown")
    for i, r in enumerate(ranked):
      medal = f"#{i+1}"
      with st.expander(
        f"{medal} {r.get('company','?')} - {r.get('role','?')} "
        f"[{r.get('role_category','?')}] "
        f"Fit:{r.get('fit_score',0)}% Score:{r.get('opportunity_score',0)}"
      ):
        st.markdown(f"**Verdict:** {r.get('one_line_verdict','')}")
        missing = r.get("missing_skills",[])
        if missing:
          st.markdown("**Missing:** " + " - ".join(missing[:5]))
        if r.get("resume_suggestions"):
          st.markdown("**Top resume fix:** " + r["resume_suggestions"][0])

        b1, b2 = st.columns(2)
        if b1.button("Save to Tracker", key=f"bsv_{i}"):
          res = save_application(r)
          if res > 0:
            st.success("Saved!")
          elif res == -1:
            st.warning("Already saved")
        if b2.button("Use for Messages", key=f"bmsg_{i}"):
          st.session_state.last_analysis = r
          st.success("Set as active - go to Messages tab")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 - APPLICATION TRACKER
# FIXED: No st.rerun() inside conditionals, uses flags instead
# ══════════════════════════════════════════════════════════════════════════════
with tab_tracker:
  st.markdown("## Application Tracker")
  st.caption("All applications - persisted in SQLite, synced to pod/tables/applications.json")

  apps = get_all_applications()

  # Add manually
  with st.expander("Add Application Manually"):
    a1,a2,a3 = st.columns(3)
    mc = a1.text_input("Company", key="t_mc", placeholder="Company name")
    mr = a2.text_input("Role",  key="t_mr", placeholder="Role title")
    mcat = a3.text_input("Category", key="t_mcat", value="General", placeholder="e.g. Data Science")
    ms = st.number_input("Fit Score (0-100)", 0, 100, 75, key="t_ms")

    if st.button("Add to Tracker", key="t_add"):
      if mc.strip() and mr.strip():
        res = save_application({
          "company":mc, "role":mr, "role_category":mcat,
          "fit_score":ms, "ats_score":0, "opportunity_score":ms,
          "matched_skills":[], "missing_skills":[],
          "resume_suggestions":[], "skill_gap_impact":{},
          "verdict":"Manually added", "cover_note":"",
          "workflow_action":"", "workflow_message":"",
          "priority":"Medium", "jd_text":""
        })
        if res > 0:
          st.success(f"Added {mc}!")
          st.rerun()
        elif res == -1:
          st.warning("Already in tracker")
      else:
        st.warning("Enter company and role")

  if not apps:
    st.info("No applications yet. Analyse a JD and click 'Save to Tracker', or add manually above.")
  else:
    # Summary metrics
    stats = get_analytics()
    s1,s2,s3,s4,s5,s6 = st.columns(6)
    s1.metric("Total",   stats["total"])
    s2.metric("Applied",  stats["applied"])
    s3.metric("Screening", stats["screening"])
    s4.metric("Interview", stats["interview"])
    s5.metric("Offer",   stats["offer"])
    s6.metric("Rejected", stats["rejected"])
    st.divider()

    # Filters
    fc1, fc2, fc3 = st.columns(3)
    f_status = fc1.selectbox("Status", ["All","Applied","Screening","Interview","Offer","Rejected"], key="t_fstatus")
    f_cat  = fc2.selectbox("Category", ["All"] + list(set(a.get("role_category","General") for a in apps)), key="t_fcat")
    f_sort  = fc3.selectbox("Sort by", ["Opportunity Score","Fit Score","Date"], key="t_fsort")

    filtered = apps
    if f_status != "All":
      filtered = [a for a in filtered if a["status"] == f_status]
    if f_cat != "All":
      filtered = [a for a in filtered if a.get("role_category","General") == f_cat]

    sort_key = {"Opportunity Score":"opportunity_score","Fit Score":"fit_score","Date":"created_at"}[f_sort]
    filtered = sorted(filtered, key=lambda x: x.get(sort_key,0), reverse=True)

    st.caption(f"Showing {len(filtered)} of {len(apps)} applications")

    STATUS_OPTIONS = ["Applied","Screening","Interview","Offer","Rejected"]

    # FIXED: Track status changes without calling st.rerun() inside the loop
    status_changed = False
    deleted_id   = None

    for a in filtered:
      fit = int(a.get("fit_score",0))
      try:
        applied = datetime.strptime(a["date_applied"],"%Y-%m-%d").date()
        age_days = (date.today()-applied).days
        age_str = f"{age_days}d"
      except Exception:
        age_str = str(a.get("date_applied",""))

      with st.container():
        c1,c2,c3,c4,c5,c6 = st.columns([2,2,1.2,0.8,2,0.6])

        c1.markdown(f"**{a['company']}**")
        c2.markdown(f"{a['role']} `{a.get('role_category','')}`")
        c3.markdown(f"{score_icon(fit)} `{fit}%`")
        c4.markdown(f"`{age_str}`")

        cur_idx = STATUS_OPTIONS.index(a.get("status","Applied"))
        new_st = c5.selectbox(
          "st", STATUS_OPTIONS, index=cur_idx,
          key=f"st_{a['id']}",
          label_visibility="collapsed"
        )

        if new_st != a.get("status"):
          update_application(a["id"], {"status": new_st})
          status_changed = True

        if c6.button("", key=f"dl_{a['id']}", help="Delete"):
          deleted_id = a["id"]

        with st.expander(f"Details - {a.get('verdict','')[:50]}"):
          note_val = a.get("notes","")
          note_new = st.text_area(
            "Notes", value=note_val, height=70,
            key=f"nt_{a['id']}",
            label_visibility="collapsed",
            placeholder="Interview notes, contacts, action items..."
          )
          if st.button("Save notes", key=f"sn_{a['id']}"):
            update_application(a["id"], {"notes": note_new})
            st.success("Saved")

          if a.get("missing_skills"):
            st.markdown("**Gaps:** " + " - ".join(a["missing_skills"][:5]))
          if a.get("cover_note"):
            st.caption(f"Cover note: {a['cover_note'][:120]}...")

        st.divider()

    # Handle deletions and refreshes AFTER the loop
    if deleted_id:
      delete_application(deleted_id)
      st.rerun()
    elif status_changed:
      st.rerun()

    # Follow-up queue
    today = date.today().isoformat()
    fups = [a for a in apps if a["status"] in ["Applied","Screening"]
         and a.get("follow_up_date","9999") <= today]
    if fups:
      st.divider()
      st.markdown("### Follow Up Today")
      for a in fups[:5]:
        st.markdown(
          f"- **{a['company']}** - {a['role']} "
          f"{score_icon(int(a.get('fit_score',0)))} {a.get('fit_score',0)}% "
          f"- Due {a.get('follow_up_date','')}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 - MARKET INTELLIGENCE
# FIXED: Category selector persists, works for any role type
# ══════════════════════════════════════════════════════════════════════════════
with tab_market:
  st.markdown("## Job Market Intelligence")
  st.caption("Analyse 10-20 JDs of any type - discover what skills the market actually demands")

  resume_text = get_resume()
  profile   = st.session_state.resume_profile
  my_skills  = set(s.lower() for s in profile.get("all_skills", []))

  col_a, col_b = st.columns([1,1])
  with col_a:
    role_cat = st.text_input(
      "Role category (what type of roles are these JDs for?)",
      value="General",
      placeholder="e.g. Data Science, Product Management, Software Engineering, Marketing",
      key="market_cat"
    )
  with col_b:
    existing_cats = get_all_role_categories()
    if existing_cats:
      st.markdown("**Previously analysed categories:**")
      st.markdown(" - ".join(existing_cats))

  jd_bulk = st.text_area(
    "Paste JDs separated by ---",
    height=220,
    placeholder="Paste 10-20 job descriptions separated by ---\nMore JDs = more accurate market intelligence\nMix seniority levels for broader insight",
    key="market_jds"
  )

  if st.button("Analyse Market", type="primary",
         disabled=not jd_bulk.strip()):
    jd_list = [j.strip() for j in jd_bulk.split("---") if len(j.strip()) > 50]
    if len(jd_list) < 3:
      st.error("Add at least 3 JDs for meaningful market intelligence")
    else:
      with st.spinner(f"Analysing {len(jd_list)} job descriptions..."):
        mdata = market_agent(jd_list, role_cat)
        save_market_skills(
          [{"skill":s["skill"],"frequency":s.get("frequency",0)}
           for s in mdata.get("top_skills",[])],
          role_cat
        )
        st.session_state.market_data = mdata
      st.success(f"Market analysis complete for {role_cat}!")

  # Load from DB if not in session
  if not st.session_state.market_data:
    db_skills = get_market_skills(role_cat)
    if db_skills:
      st.session_state.market_data = {
        "top_skills": [{"skill":s["skill"],"frequency":s["frequency"],"importance":"-"} for s in db_skills]
      }

  mdata = st.session_state.market_data
  if mdata and mdata.get("top_skills"):
    st.divider()
    if mdata.get("role_summary"):
      st.info(mdata["role_summary"])

    st.markdown(f"### Top Skills - {role_cat}")
    have_n, miss_n = 0, 0

    for sd in mdata["top_skills"][:15]:
      skill = sd.get("skill","")
      freq = int(sd.get("frequency",0))
      have = any(skill.lower() in ms or ms in skill.lower() for ms in my_skills) if my_skills else False
      color = "#1D9E75" if have else "#A32D2D"
      label = " You have this" if have else " Missing"
      if have: have_n += 1
      else: miss_n += 1

      st.markdown(
        f'<div style="margin-bottom:10px">'
        f'<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:3px">'
        f'<span style="font-weight:500">{skill}</span>'
        f'<span style="color:{color};font-size:12px">{label} - {freq}% of JDs</span>'
        f'</div>'
        f'<div style="background:#e8e6de;border-radius:4px;height:10px">'
        f'<div style="background:{color};width:{min(freq,100)}%;height:10px;border-radius:4px;opacity:0.85"></div>'
        f'</div></div>',
        unsafe_allow_html=True
      )

    total_top = have_n + miss_n
    if total_top > 0:
      cov = round((have_n/total_top)*100)
      st.info(f"You have **{have_n}/{total_top}** top market skills ({cov}% market coverage for {role_cat})")

    mc1, mc2 = st.columns(2)
    with mc1:
      if mdata.get("emerging_skills"):
        st.markdown("### Emerging Skills to Watch")
        for s in mdata["emerging_skills"][:5]:
          st.markdown(f"- {s}")
    with mc2:
      if mdata.get("recommended_learning_order"):
        st.markdown("### Recommended Learning Order")
        for i, s in enumerate(mdata["recommended_learning_order"][:5], 1):
          st.markdown(f"**{i}.** {s}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 - MESSAGE DRAFTER
# FIXED: Auto-fills from any analysis, not just Data Science
# ══════════════════════════════════════════════════════════════════════════════
with tab_messages:
  st.markdown("## Message Drafter")
  st.caption("5 message types - auto-filled from your last analysis")

  last = st.session_state.last_analysis or {}

  mc1, mc2 = st.columns(2)
  d_co   = mc1.text_input("Company", value=last.get("company",""), key="msg_co")
  d_ro   = mc2.text_input("Role",  value=last.get("role",""),  key="msg_ro")
  d_skills = last.get("matched_skills", [])

  d_ctx = st.text_input(
    "Context (optional)",
    placeholder="e.g. Referred by Priya - Spoke at meetup - Had screening call on Monday",
    key="msg_ctx"
  )

  msg_type = st.selectbox("Message type", [
    "cold_outreach", "follow_up", "referral_request", "thank_you", "post_interview"
  ], format_func=lambda x: {
    "cold_outreach":  "Cold Outreach - First contact with recruiter",
    "follow_up":    "Follow-Up - No reply after 1 week",
    "referral_request": "Referral Request - Ask a connection for a referral",
    "thank_you":    "Thank You - After a screening call",
    "post_interview":  "Post-Interview - After a technical/functional round"
  }[x], key="msg_type")

  if st.button("Generate Message", type="primary", key="msg_gen"):
    if not d_co.strip() or not d_ro.strip():
      st.warning("Enter company and role first")
    else:
      with st.spinner("Drafting..."):
        msg = message_agent(d_co, d_ro, d_skills, msg_type, d_ctx)

      st.markdown("### Your Message")
      st.text_area(
        "Edit before sending",
        value=msg, height=260,
        label_visibility="collapsed",
        key="msg_output"
      )
      st.caption(" Replace **[Recruiter Name]** and **[Your Name]** before sending")
      st.info("Select all, then Ctrl+C on Windows to copy")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 - INTERVIEW SIMULATOR
# FIXED: State machine approach - no rerun inside loops
# ══════════════════════════════════════════════════════════════════════════════
with tab_interview:
  st.markdown("## AI Recruiter Simulator")
  st.caption("5-round mock interview - Technical + Communication + Confidence scoring - Any role")

  last = st.session_state.last_analysis or {}

  ic1, ic2 = st.columns(2)
  i_co = ic1.text_input("Company", value=last.get("company",""), key="int_co")
  i_ro = ic2.text_input("Role",  value=last.get("role",""),  key="int_ro")
  i_miss = last.get("missing_skills", [])

  btn_start, btn_reset, _ = st.columns([1,1,3])

  if btn_start.button("▶ Start Interview", type="primary", key="int_start"):
    if not i_co.strip() or not i_ro.strip():
      st.warning("Enter company and role first")
    else:
      with st.spinner("Preparing Question 1..."):
        q = interview_question_agent(i_co, i_ro, i_miss, 1)
      st.session_state.int_active  = True
      st.session_state.int_question = q
      st.session_state.int_round  = 1
      st.session_state.int_company = i_co
      st.session_state.int_role   = i_ro
      st.session_state.int_missing = i_miss
      st.session_state.int_scores  = []

  if btn_reset.button("↺ Reset", key="int_reset"):
    for k in ["int_active","int_question","int_round","int_company","int_role","int_scores"]:
      st.session_state[k] = _DEFAULTS[k]

  # Active session
  if st.session_state.int_active and st.session_state.int_question:
    st.divider()
    rnd = st.session_state.int_round
    st.progress(min(rnd/5,1.0), text=f"Round {rnd} of 5 - {st.session_state.int_company}")

    # Question
    st.markdown(
      f'<div style="background:var(--color-background-secondary);'
      f'border-left:4px solid #185FA5;padding:16px 20px;'
      f'border-radius:0 10px 10px 0;margin:12px 0">'
      f'<p style="font-size:11px;color:#888;margin:0 0 6px">'
      f' AI Recruiter - {st.session_state.int_company} - {st.session_state.int_role}</p>'
      f'<p style="font-size:15px;margin:0;line-height:1.5">{st.session_state.int_question}</p>'
      f'</div>',
      unsafe_allow_html=True
    )

    with st.expander(" Answering tips"):
      st.markdown("""
**STAR format:** Situation - Task - Action - Result
- Include specific numbers and outcomes ("increased by 30%", "reduced time by 2 hours")
- Keep answer under 2 minutes (about 200-250 words written)
- Be specific - avoid vague answers like "I worked on a project"
""")

    answer = st.text_area(
      "Your answer",
      height=160,
      placeholder="Type your answer here...",
      key=f"int_ans_{rnd}"
    )

    if st.button("Submit Answer", type="primary", key=f"int_sub_{rnd}"):
      if not answer.strip():
        st.warning("Write your answer first")
      else:
        with st.spinner("Evaluating your answer..."):
          ev = interview_evaluate_agent(
            st.session_state.int_question,
            answer,
            st.session_state.int_role
          )

        # Save to DB
        save_interview_session({
          "company":      st.session_state.int_company,
          "role":        st.session_state.int_role,
          "question":      st.session_state.int_question,
          "answer":       answer,
          "score":       int(ev.get("overall_score",0)),
          "technical_score":  int(ev.get("technical_score",0)),
          "communication_score":int(ev.get("communication_score",0)),
          "confidence_score":  int(ev.get("confidence_score",0)),
          "feedback":      ev.get("overall_feedback",""),
          "strengths":     ev.get("strengths",[]),
          "improvements":    ev.get("improvements",[])
        })
        st.session_state.int_scores.append(int(ev.get("overall_score",0)))

        # Score display
        tech = int(ev.get("technical_score",0))
        comm = int(ev.get("communication_score",0))
        conf = int(ev.get("confidence_score",0))
        ov  = int(ev.get("overall_score",0))

        sc1,sc2,sc3,sc4 = st.columns(4)
        sc1.metric("Technical",   f"{tech}/10")
        sc2.metric("Communication", f"{comm}/10")
        sc3.metric("Confidence",  f"{conf}/10")
        sc4.metric("Overall",    f"{ov}/10",
              delta="STAR " if ev.get("star_used") else "No STAR")

        st.markdown(
          f'<div style="border:0.5px solid var(--color-border-tertiary);'
          f'border-radius:10px;padding:16px;margin:12px 0">'
          f'<p style="margin:0">{ev.get("overall_feedback","")}</p>'
          f'</div>',
          unsafe_allow_html=True
        )

        f1, f2 = st.columns(2)
        with f1:
          st.markdown("**What worked**")
          for s in ev.get("strengths",[]):
            st.markdown(f"- {s}")
        with f2:
          st.markdown("**Improve this**")
          for s in ev.get("improvements",[]):
            st.markdown(f"- {s}")

        st.info(f"**A great answer would include:** {ev.get('ideal_elements','')}")

        # Next question
        next_rnd = rnd + 1
        if next_rnd <= 5:
          if st.button(f"Next Question ({next_rnd}/5)", key=f"int_next_{rnd}"):
            with st.spinner(f"Preparing Q{next_rnd}..."):
              nq = interview_question_agent(
                st.session_state.int_company,
                st.session_state.int_role,
                st.session_state.int_missing,
                next_rnd
              )
            st.session_state.int_round  = next_rnd
            st.session_state.int_question = nq
            st.rerun()
        else:
          scores = st.session_state.int_scores
          avg = round(sum(scores)/len(scores)) if scores else 0
          st.success(f" Interview complete! Average score: {avg}/10")

          avgs = get_interview_avg_scores(
            st.session_state.int_company,
            st.session_state.int_role
          )
          if avgs["total_sessions"] > 0:
            st.markdown(
              f"**All-time:** Overall {avgs['overall']}/10 - "
              f"Technical {avgs['technical']} - "
              f"Communication {avgs['communication']} - "
              f"Confidence {avgs['confidence']}"
            )

  # Session history
  sessions = get_interview_sessions(
    st.session_state.int_company,
    st.session_state.int_role
  )
  if sessions:
    with st.expander(f" Session History ({len(sessions)} answers)"):
      for s in sessions[:10]:
        ov = int(s.get("score",0))
        st.markdown(
          f"{score_icon(ov*10)} **Q:** {s['question'][:80]}... "
          f"**Score:** {ov}/10 - "
          f"T:{s.get('technical_score',0)} "
          f"C:{s.get('communication_score',0)} "
          f"Conf:{s.get('confidence_score',0)}"
        )
        st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 - FULL CAREER WORKFLOW
# ══════════════════════════════════════════════════════════════════════════════
with tab_workflow:
  st.markdown("## Full Career Workflow")
  st.caption("One click: Bulk Analysis + Employability Score + Resume Optimisation")
  st.caption("Lemma pattern: input - state - action - approval - outcome")

  resume_text = get_resume()
  profile   = st.session_state.resume_profile

  if not resume_text:
    st.warning("Upload your resume in the sidebar first")
  else:
    st.markdown("""
**This workflow runs 4 agents in sequence:**

`JDAgent x N` - `MatchingAgent x N` - `EmployabilityAgent` - `ResumeOptimizerAgent`

Each step writes results to `pod/tables/` and `pod/files/` (Lemma pod structure).
    """)

    wf_jds = st.text_area(
      "Paste JDs separated by ---",
      height=200,
      placeholder="Paste 5-20 job descriptions (any role type) separated by ---",
      key="wf_jds"
    )

    if st.button("Run Full Career Workflow", type="primary", disabled=not wf_jds.strip()):
      jd_list = [j.strip() for j in wf_jds.split("---") if len(j.strip()) > 50]
      if len(jd_list) < 2:
        st.error("Need at least 2 JDs")
      else:
        prog = st.progress(0)
        stat = st.empty()

        def _wf_prog(current, total, msg):
          prog.progress(current/total)
          stat.caption(msg)

        orch   = OrchestrationAgent()
        analytics = get_analytics()
        mdata   = st.session_state.market_data or {}

        with st.spinner("Running full workflow..."):
          # Step 1: Bulk rank
          stat.caption("Running bulk JD analysis...")
          prog.progress(0.2)
          ranked = orch.run_bulk_analysis(resume_text, jd_list, _wf_prog)

          # Step 2: Employability
          stat.caption("Calculating employability score...")
          prog.progress(0.7)
          market_skills = mdata.get("top_skills",[])
          emp = employability_agent(profile, market_skills, analytics)
          save_employability(emp)

          # Step 3: Resume optimisation
          stat.caption("Optimising resume against all JDs...")
          prog.progress(0.9)
          optimizer = resume_optimizer_agent(resume_text, jd_list)

        prog.empty()
        stat.empty()

        st.session_state.career_result = {
          "ranked": ranked,
          "employability": emp,
          "optimizer": optimizer
        }
        st.success("Workflow complete!")

    # Show results
    cr = st.session_state.career_result
    if cr:
      st.divider()

      # Employability
      emp = cr.get("employability",{})
      if emp:
        st.markdown("### Employability Score")
        e1,e2,e3,e4,e5 = st.columns(5)
        e1.metric("Overall",    f"{emp.get('overall_score',0)}%")
        e2.metric("Resume",    f"{emp.get('resume_score',0)}%")
        e3.metric("Skill Match",  f"{emp.get('skill_match_score',0)}%")
        e4.metric("Market Demand", f"{emp.get('market_demand_score',0)}%")
        e5.metric("App Success",  f"{emp.get('application_score',0)}%")

        recs = emp.get("top_recommendations",[])
        if recs:
          st.markdown("**Your learning roadmap:**")
          for r in recs:
            ra, rb = st.columns([3,1])
            ra.markdown(f"- **{r['action']}** - {r.get('reason','')}")
            rb.markdown(f"**+{r['impact']}%** in ~{r['time_weeks']}w")

      st.divider()

      # Ranked table
      ranked = cr.get("ranked",[])
      if ranked:
        st.markdown(f"### Opportunity Ranking ({len(ranked)} JDs)")
        action_map = {
          "IMMEDIATE_APPLY":" Apply Now",
          "APPLY_WITH_TAILORING":" Tailor First",
          "UPSKILL_FIRST":" Upskill"
        }
        for i, r in enumerate(ranked[:10]):
          medal = f"#{i+1}"
          st.markdown(
            f"{medal} **{r.get('company','?')}** - {r.get('role','?')} "
            f"[{r.get('role_category','?')}] "
            f"| Fit:{r.get('fit_score',0)}% "
            f"Score:{r.get('opportunity_score',0)} "
            f"| {action_map.get(r.get('workflow_action',''),'-')}"
          )

      st.divider()

      # Resume optimiser
      opt = cr.get("optimizer",{})
      if opt:
        st.markdown("### Resume Optimisation")
        if opt.get("optimized_summary"):
          st.markdown("**Updated summary (replace yours with this):**")
          st.info(opt["optimized_summary"])
        if opt.get("quick_wins"):
          st.markdown("**Quick wins - do these today:**")
          for w in opt["quick_wins"]:
            st.markdown(f"- {w}")
        if opt.get("missing_keywords"):
          st.markdown("**Missing keywords to add:**")
          html = " ".join(
            pill(k,"#FAEEDA","#633806")
            for k in opt["missing_keywords"][:12]
          )
          st.markdown(html, unsafe_allow_html=True)
        if opt.get("project_suggestions"):
          st.markdown("**Project ideas to close gaps:**")
          for p in opt["project_suggestions"]:
            st.markdown(f"- {p}")

    # Workflow execution log (Lemma transparency)
    logs = get_workflow_logs(10)
    if logs:
      with st.expander(" Workflow Execution Log (pod/tables/workflow_log)"):
        for log in logs:
          st.markdown(
            f"`{log['created_at']}` **{log['workflow']}** - "
            f"{log['status']} - {log['details']} - {log['duration_ms']}ms"
          )
