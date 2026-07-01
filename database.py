# database.py — CareerPilot AI v3
# Lemma pod-aware database layer
# Fixed: Windows path issues, no st.rerun() triggers, safe JSON handling

import sqlite3
import json
import os
import logging
from datetime import datetime, date, timedelta
from pathlib import Path

# ── PATHS (Windows safe using pathlib) ───────────────────────────────────────
BASE_DIR  = Path(__file__).parent
DB_PATH   = BASE_DIR / "careerpilot.db"
LOG_DIR   = BASE_DIR / "logs"
POD_DIR   = BASE_DIR / "pod"
TABLES_DIR = POD_DIR / "tables"
FILES_DIR  = POD_DIR / "files"

LOG_DIR.mkdir(exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)
FILES_DIR.mkdir(parents=True, exist_ok=True)

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=str(LOG_DIR / "careerpilot.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("careerpilot")


def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _safe_json_loads(value, default):
    """Never crashes on bad JSON."""
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _sync_pod_table(table_name: str, rows: list):
    """Mirror a DB table to the pod/tables/ directory as JSON (Lemma pattern)."""
    try:
        path = TABLES_DIR / f"{table_name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Pod sync failed for {table_name}: {e}")


def _sync_pod_file(filename: str, content):
    """Mirror a file to the pod/files/ directory."""
    try:
        path = FILES_DIR / filename
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(content, str):
                f.write(content)
            else:
                json.dump(content, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Pod file sync failed for {filename}: {e}")


# ── INIT ──────────────────────────────────────────────────────────────────────

def init_db():
    conn = _conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS resume (
            id          INTEGER PRIMARY KEY,
            text        TEXT NOT NULL,
            filename    TEXT,
            uploaded_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # FIXED: UNIQUE constraint prevents duplicates without crashing
    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            company             TEXT NOT NULL,
            role                TEXT NOT NULL,
            role_category       TEXT DEFAULT 'General',
            jd_text             TEXT DEFAULT '',
            fit_score           INTEGER DEFAULT 0,
            ats_score           INTEGER DEFAULT 0,
            opportunity_score   INTEGER DEFAULT 0,
            matched_skills      TEXT DEFAULT '[]',
            missing_skills      TEXT DEFAULT '[]',
            resume_suggestions  TEXT DEFAULT '[]',
            skill_gap_impact    TEXT DEFAULT '{}',
            verdict             TEXT DEFAULT '',
            cover_note          TEXT DEFAULT '',
            workflow_action     TEXT DEFAULT '',
            workflow_message    TEXT DEFAULT '',
            status              TEXT DEFAULT 'Applied',
            priority            TEXT DEFAULT 'Medium',
            date_applied        TEXT DEFAULT (date('now')),
            follow_up_date      TEXT,
            notes               TEXT DEFAULT '',
            created_at          TEXT DEFAULT (datetime('now')),
            updated_at          TEXT DEFAULT (datetime('now')),
            UNIQUE(company, role)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS market_skills (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            skill         TEXT NOT NULL,
            frequency     INTEGER DEFAULT 1,
            role_category TEXT DEFAULT 'General',
            analyzed_at   TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            company             TEXT DEFAULT '',
            role                TEXT DEFAULT '',
            question            TEXT DEFAULT '',
            answer              TEXT DEFAULT '',
            score               INTEGER DEFAULT 0,
            technical_score     INTEGER DEFAULT 0,
            communication_score INTEGER DEFAULT 0,
            confidence_score    INTEGER DEFAULT 0,
            feedback            TEXT DEFAULT '',
            strengths           TEXT DEFAULT '[]',
            improvements        TEXT DEFAULT '[]',
            created_at          TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS workflow_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow    TEXT DEFAULT '',
            status      TEXT DEFAULT '',
            details     TEXT DEFAULT '',
            duration_ms INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS employability (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            overall_score       INTEGER DEFAULT 0,
            resume_score        INTEGER DEFAULT 0,
            skill_match_score   INTEGER DEFAULT 0,
            market_demand_score INTEGER DEFAULT 0,
            application_score   INTEGER DEFAULT 0,
            recommendations     TEXT DEFAULT '[]',
            captured_at         TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    logger.info("DB initialised")


# ── RESUME ────────────────────────────────────────────────────────────────────



def reset_workspace():
    """Clear all app data and pod mirrors for a fresh demo run."""
    conn = _conn()
    for table in [
        "resume",
        "applications",
        "market_skills",
        "interview_sessions",
        "workflow_log",
        "employability",
    ]:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()

    for name in [
        "applications",
        "market_skills",
        "interview_sessions",
        "workflow_log",
    ]:
        _sync_pod_table(name, [])

    for filename, content in {
        "resume.md": "# Resume\n\n",
        "candidate_profile.json": {},
        "employability_report.json": {},
    }.items():
        _sync_pod_file(filename, content)

    logger.info("Workspace reset")

def save_resume(text: str, filename: str = "resume.pdf"):
    conn = _conn()
    conn.execute("DELETE FROM resume")
    conn.execute("INSERT INTO resume (text, filename) VALUES (?,?)", (text, filename))
    conn.commit()
    conn.close()
    _sync_pod_file("resume.md", f"# Resume\n\n{text}")
    logger.info(f"Resume saved: {filename}")


def get_resume() -> str:
    conn = _conn()
    row = conn.execute("SELECT text FROM resume ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row["text"] if row else ""


# ── APPLICATIONS ──────────────────────────────────────────────────────────────

def save_application(data: dict) -> int:
    """
    Returns: new id (>0), -1 if duplicate, -2 on other error
    FIXED: Uses INSERT OR IGNORE so duplicates never crash
    """
    conn = _conn()
    follow_up = (date.today() + timedelta(days=7)).isoformat()
    try:
        c = conn.execute("""
            INSERT OR IGNORE INTO applications
            (company, role, role_category, jd_text,
             fit_score, ats_score, opportunity_score,
             matched_skills, missing_skills, resume_suggestions,
             skill_gap_impact, verdict, cover_note,
             workflow_action, workflow_message,
             status, priority, follow_up_date)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get("company", "Unknown"),
            data.get("role", "Unknown"),
            data.get("role_category", "General"),
            data.get("jd_text", ""),
            int(data.get("fit_score", 0)),
            int(data.get("ats_score", 0)),
            int(data.get("opportunity_score", 0)),
            json.dumps(data.get("matched_skills", [])),
            json.dumps(data.get("missing_skills", [])),
            json.dumps(data.get("resume_suggestions", [])),
            json.dumps(data.get("skill_gap_impact", {})),
            str(data.get("verdict", "")),
            str(data.get("cover_note", "")),
            str(data.get("workflow_action", "")),
            str(data.get("workflow_message", "")),
            str(data.get("status", "Applied")),
            str(data.get("priority", "Medium")),
            follow_up
        ))
        new_id = c.lastrowid
        conn.commit()

        if new_id:
            apps = get_all_applications()
            _sync_pod_table("applications", apps)
            logger.info(f"Application saved: {data.get('company')} — {data.get('role')} id={new_id}")
            return new_id
        else:
            logger.warning(f"Duplicate skipped: {data.get('company')} — {data.get('role')}")
            return -1
    except Exception as e:
        logger.error(f"save_application error: {e}")
        return -2
    finally:
        conn.close()


def get_all_applications() -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM applications ORDER BY opportunity_score DESC, created_at DESC"
    ).fetchall()
    conn.close()
    apps = []
    for row in rows:
        app = dict(row)
        app["matched_skills"]     = _safe_json_loads(app.get("matched_skills"), [])
        app["missing_skills"]     = _safe_json_loads(app.get("missing_skills"), [])
        app["resume_suggestions"] = _safe_json_loads(app.get("resume_suggestions"), [])
        app["skill_gap_impact"]   = _safe_json_loads(app.get("skill_gap_impact"), {})
        apps.append(app)
    return apps


def update_application(app_id: int, updates: dict):
    if not updates:
        return
    fields = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [app_id]
    conn = _conn()
    conn.execute(
        f"UPDATE applications SET {fields}, updated_at=datetime('now') WHERE id=?",
        values
    )
    conn.commit()
    conn.close()


def delete_application(app_id: int):
    conn = _conn()
    conn.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()
    conn.close()
    logger.info(f"Application deleted: id={app_id}")


def application_exists(company: str, role: str) -> bool:
    conn = _conn()
    row = conn.execute(
        "SELECT id FROM applications WHERE company=? AND role=?",
        (company, role)
    ).fetchone()
    conn.close()
    return row is not None


# ── MARKET SKILLS ─────────────────────────────────────────────────────────────

def save_market_skills(skills: list, role_category: str = "General"):
    conn = _conn()
    conn.execute("DELETE FROM market_skills WHERE role_category=?", (role_category,))
    for s in skills:
        conn.execute(
            "INSERT INTO market_skills (skill, frequency, role_category) VALUES (?,?,?)",
            (s.get("skill",""), int(s.get("frequency", 0)), role_category)
        )
    conn.commit()
    conn.close()
    _sync_pod_table("market_skills", skills)
    logger.info(f"Market skills saved: {len(skills)} for {role_category}")


def get_market_skills(role_category: str = "General") -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT skill, frequency FROM market_skills WHERE role_category=? ORDER BY frequency DESC",
        (role_category,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_role_categories() -> list:
    """Returns all unique role categories with saved market data."""
    conn = _conn()
    rows = conn.execute(
        "SELECT DISTINCT role_category FROM market_skills ORDER BY role_category"
    ).fetchall()
    conn.close()
    return [r["role_category"] for r in rows]


# ── INTERVIEW SESSIONS ────────────────────────────────────────────────────────

def save_interview_session(data: dict):
    conn = _conn()
    conn.execute("""
        INSERT INTO interview_sessions
        (company, role, question, answer, score,
         technical_score, communication_score, confidence_score,
         feedback, strengths, improvements)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data.get("company",""), data.get("role",""),
        data.get("question",""), data.get("answer",""),
        int(data.get("score",0)),
        int(data.get("technical_score",0)),
        int(data.get("communication_score",0)),
        int(data.get("confidence_score",0)),
        data.get("feedback",""),
        json.dumps(data.get("strengths",[])),
        json.dumps(data.get("improvements",[]))
    ))
    conn.commit()
    conn.close()


def get_interview_sessions(company: str = None, role: str = None) -> list:
    conn = _conn()
    if company and role:
        rows = conn.execute(
            "SELECT * FROM interview_sessions WHERE company=? AND role=? ORDER BY created_at DESC",
            (company, role)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM interview_sessions ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    conn.close()
    sessions = []
    for row in rows:
        s = dict(row)
        s["strengths"]    = _safe_json_loads(s.get("strengths"), [])
        s["improvements"] = _safe_json_loads(s.get("improvements"), [])
        sessions.append(s)
    return sessions


def get_interview_avg_scores(company: str, role: str) -> dict:
    conn = _conn()
    row = conn.execute("""
        SELECT AVG(technical_score) as tech,
               AVG(communication_score) as comm,
               AVG(confidence_score) as conf,
               AVG(score) as overall,
               COUNT(*) as total
        FROM interview_sessions WHERE company=? AND role=?
    """, (company, role)).fetchone()
    conn.close()
    if row and row["total"]:
        return {
            "technical":      round(row["tech"] or 0, 1),
            "communication":  round(row["comm"] or 0, 1),
            "confidence":     round(row["conf"] or 0, 1),
            "overall":        round(row["overall"] or 0, 1),
            "total_sessions": row["total"]
        }
    return {"technical":0, "communication":0, "confidence":0, "overall":0, "total_sessions":0}


# ── WORKFLOW LOG ──────────────────────────────────────────────────────────────

def log_workflow(workflow: str, status: str, details: str = "", duration_ms: int = 0):
    conn = _conn()
    conn.execute(
        "INSERT INTO workflow_log (workflow, status, details, duration_ms) VALUES (?,?,?,?)",
        (workflow, status, details, duration_ms)
    )
    conn.commit()
    conn.close()
    logger.info(f"Workflow [{workflow}] {status} — {details}")


def get_workflow_logs(limit: int = 20) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM workflow_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── EMPLOYABILITY ─────────────────────────────────────────────────────────────

def save_employability(data: dict):
    conn = _conn()
    conn.execute("""
        INSERT INTO employability
        (overall_score, resume_score, skill_match_score,
         market_demand_score, application_score, recommendations)
        VALUES (?,?,?,?,?,?)
    """, (
        int(data.get("overall_score",0)),
        int(data.get("resume_score",0)),
        int(data.get("skill_match_score",0)),
        int(data.get("market_demand_score",0)),
        int(data.get("application_score",0)),
        json.dumps(data.get("top_recommendations",[]))
    ))
    conn.commit()
    conn.close()
    _sync_pod_file("employability_report.json", data)


def get_employability() -> dict:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM employability ORDER BY captured_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        r = dict(row)
        r["top_recommendations"] = _safe_json_loads(r.get("recommendations"), [])
        return r
    return {}


# ── ANALYTICS ─────────────────────────────────────────────────────────────────

def get_analytics() -> dict:
    conn = _conn()
    apps = conn.execute("SELECT * FROM applications").fetchall()
    total = len(apps)
    conn.close()

    if total == 0:
        return {
            "total":0, "applied":0, "screening":0, "interview":0,
            "offer":0, "rejected":0, "avg_fit":0, "avg_ats":0,
            "employability":0, "response_rate":0,
            "top_missing_skills":[], "fit_distribution":[],
            "role_categories":[]
        }

    statuses   = [r["status"] for r in apps]
    fit_scores = [r["fit_score"] for r in apps if r["fit_score"]]
    ats_scores = [r["ats_score"] for r in apps if r["ats_score"]]

    avg_fit = round(sum(fit_scores)/len(fit_scores)) if fit_scores else 0
    avg_ats = round(sum(ats_scores)/len(ats_scores)) if ats_scores else 0
    employability = round(avg_fit * 0.6 + avg_ats * 0.4)

    responded     = sum(1 for s in statuses if s in ["Screening","Interview","Offer"])
    response_rate = round((responded/total)*100) if total else 0

    # Skill gaps across ALL role categories
    skill_count = {}
    for row in apps:
        missing = _safe_json_loads(row["missing_skills"], [])
        for skill in missing:
            skill_count[skill] = skill_count.get(skill, 0) + 1
    top_missing = sorted(skill_count.items(), key=lambda x: x[1], reverse=True)[:8]

    # Fit distribution
    buckets = {"0-30":0, "31-50":0, "51-70":0, "71-85":0, "86-100":0}
    for s in fit_scores:
        if s <= 30:   buckets["0-30"]   += 1
        elif s <= 50: buckets["31-50"]  += 1
        elif s <= 70: buckets["51-70"]  += 1
        elif s <= 85: buckets["71-85"]  += 1
        else:         buckets["86-100"] += 1

    # Role categories breakdown
    cat_count = {}
    for row in apps:
        cat = row["role_category"] or "General"
        cat_count[cat] = cat_count.get(cat, 0) + 1

    return {
        "total":           total,
        "applied":         statuses.count("Applied"),
        "screening":       statuses.count("Screening"),
        "interview":       statuses.count("Interview"),
        "offer":           statuses.count("Offer"),
        "rejected":        statuses.count("Rejected"),
        "avg_fit":         avg_fit,
        "avg_ats":         avg_ats,
        "employability":   employability,
        "response_rate":   response_rate,
        "top_missing_skills": top_missing,
        "fit_distribution":   list(buckets.items()),
        "role_categories":    sorted(cat_count.items(), key=lambda x: x[1], reverse=True)
    }
