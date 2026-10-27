import json
import os
import secrets
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from io import BytesIO

from database import delete_brief, get_brief, init_db, list_briefs, save_brief
from scope_engine import analyze_request

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["DATABASE"] = os.getenv("DATABASE_PATH") or str(BASE_DIR / "instance" / "scopenote.sqlite3")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

init_db(app.config["DATABASE"])


def gemini_status() -> str:
    return "Connected" if os.getenv("GEMINI_API_KEY", "").strip() else "Local mode"


def markdown_report(brief: dict) -> str:
    data = brief["analysis"]
    sections = [
        f"# {data.get('title', 'Client brief')}",
        f"\n**Project type:** {brief.get('project_type', 'Not specified')}  \n**Analysis mode:** {brief.get('mode', 'Unknown')}  \n**Created:** {brief.get('created_at', '')}",
        f"\n## Summary\n{data.get('summary', '')}",
    ]
    list_sections = [
        ("Goals", "goals"), ("Requirements", "requirements"), ("Deliverables", "deliverables"),
        ("Questions for the client", "questions"), ("Scope boundaries to confirm", "boundaries"),
        ("Acceptance criteria", "acceptance_criteria"),
    ]
    for heading, key in list_sections:
        sections.append(f"\n## {heading}\n" + "\n".join(f"- {item}" for item in data.get(key, [])))
    sections.append("\n## Risks\n" + "\n".join(f"- **{item.get('level', 'Medium')}: {item.get('title', 'Risk')}** — {item.get('detail', '')}" for item in data.get("risks", [])))
    sections.append(f"\n## Client confirmation draft\n{data.get('client_summary', '')}")
    sections.append(f"\n## Recommended next step\n{data.get('suggested_next_step', '')}")
    sections.append("\n## Original client message\n> " + brief.get("source_text", "").replace("\n", "\n> "))
    return "\n".join(sections).strip() + "\n"


@app.get("/")
def index():
    saved_id = request.args.get("brief", type=int)
    saved_brief = get_brief(app.config["DATABASE"], saved_id) if saved_id else None
    if saved_id and saved_brief is None:
        abort(404)
    return render_template(
        "index.html",
        active_page="new",
        gemini_status=gemini_status(),
        saved_brief=saved_brief,
        current_year=datetime.now().year,
    )


@app.post("/api/analyze")
def api_analyze():
    payload = request.get_json(silent=True) or {}
    source_text = payload.get("client_message", "")
    if not isinstance(source_text, str):
        return jsonify({"ok": False, "error": "Enter the client's message as text."}), 400
    source_text = source_text.strip()
    if len(source_text) < 20:
        return jsonify({"ok": False, "error": "Add a little more detail. The client message must contain at least 20 characters."}), 400
    if len(source_text) > 20000:
        return jsonify({"ok": False, "error": "The client message is too long. Please keep it under 20,000 characters."}), 400

    project_type = str(payload.get("project_type", "Other"))[:80]
    budget = str(payload.get("budget", ""))[:160]
    deadline = str(payload.get("deadline", ""))[:160]
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"

    analysis, mode, warning = analyze_request(source_text, project_type, budget, deadline, api_key, model)
    brief_id = save_brief(app.config["DATABASE"], project_type, source_text, analysis, mode)
    return jsonify({
        "ok": True,
        "id": brief_id,
        "analysis": analysis,
        "mode": mode,
        "warning": warning,
        "export_url": url_for("export_brief", brief_id=brief_id),
        "saved_url": url_for("index", brief=brief_id),
    })


@app.get("/history")
def history():
    briefs = list_briefs(app.config["DATABASE"])
    return render_template("history.html", briefs=briefs, active_page="history", current_year=datetime.now().year)


@app.post("/brief/<int:brief_id>/delete")
def remove_brief(brief_id: int):
    delete_brief(app.config["DATABASE"], brief_id)
    flash("Brief deleted.", "success")
    return redirect(url_for("history"))


@app.get("/export/<int:brief_id>.md")
def export_brief(brief_id: int):
    brief = get_brief(app.config["DATABASE"], brief_id)
    if brief is None:
        abort(404)
    content = markdown_report(brief).encode("utf-8")
    safe_name = "".join(char.lower() if char.isalnum() else "-" for char in brief["analysis"].get("title", "client-brief"))
    safe_name = "-".join(part for part in safe_name.split("-") if part)[:60] or "client-brief"
    return send_file(
        BytesIO(content),
        mimetype="text/markdown; charset=utf-8",
        as_attachment=True,
        download_name=f"{safe_name}.md",
    )


@app.get("/health")
def health():
    return jsonify({"ok": True, "app": "ScopeNote", "analysis_mode": gemini_status()})


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "true").lower() == "true")
