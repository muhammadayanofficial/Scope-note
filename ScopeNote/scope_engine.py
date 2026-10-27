import json
import re
from typing import Any

import requests

MODEL_DEFAULT = "gemini-3.8-flash"

OUTPUT_SHAPE = {
    "title": "Short, clear project title",
    "summary": "A concise summary of what the client appears to need.",
    "goals": ["Project goal"],
    "requirements": ["Specific requirement inferred from the message"],
    "deliverables": ["Concrete output to deliver"],
    "questions": ["Important question to ask the client before starting"],
    "risks": [{"title": "Risk title", "detail": "Why it matters and how to reduce it", "level": "Medium"}],
    "boundaries": ["Proposed scope boundary to confirm"],
    "acceptance_criteria": ["How the work can be checked and accepted"],
    "client_summary": "A polished, professional summary that can be sent to the client for confirmation.",
    "suggested_next_step": "One practical next step.",
}


def _clean_text(value: Any, max_length: int = 20000) -> str:
    if not isinstance(value, str):
        return ""
    value = value.replace("\x00", " ")
    return value.strip()[:max_length]


def _as_list(value: Any, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip()[:500])
        if len(cleaned) >= limit:
            break
    return cleaned


def normalize_analysis(raw: Any, original_text: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("The analysis response was not a JSON object.")

    title = raw.get("title")
    summary = raw.get("summary")
    if not isinstance(title, str) or not title.strip():
        title = derive_title(original_text)
    if not isinstance(summary, str) or not summary.strip():
        summary = summarize_text(original_text)

    risks = []
    incoming_risks = raw.get("risks", [])
    if isinstance(incoming_risks, list):
        for risk in incoming_risks[:6]:
            if isinstance(risk, str):
                risks.append({"title": risk[:120], "detail": "Confirm this point with the client before committing to the scope.", "level": "Medium"})
            elif isinstance(risk, dict):
                risk_title = str(risk.get("title", "Potential project risk")).strip()[:120]
                detail = str(risk.get("detail", "Confirm the details with the client.")).strip()[:500]
                level = str(risk.get("level", "Medium")).strip().title()
                if level not in {"Low", "Medium", "High"}:
                    level = "Medium"
                risks.append({"title": risk_title or "Potential project risk", "detail": detail or "Confirm the details with the client.", "level": level})

    result = {
        "title": title.strip()[:160],
        "summary": summary.strip()[:1200],
        "goals": _as_list(raw.get("goals"), 6),
        "requirements": _as_list(raw.get("requirements"), 10),
        "deliverables": _as_list(raw.get("deliverables"), 8),
        "questions": _as_list(raw.get("questions"), 10),
        "risks": risks,
        "boundaries": _as_list(raw.get("boundaries"), 8),
        "acceptance_criteria": _as_list(raw.get("acceptance_criteria"), 8),
        "client_summary": str(raw.get("client_summary", "")).strip()[:3000],
        "suggested_next_step": str(raw.get("suggested_next_step", "Confirm the requirements and success criteria with the client.")).strip()[:600],
    }

    if not result["goals"]:
        result["goals"] = [result["summary"]]
    if not result["requirements"]:
        result["requirements"] = extract_requirements(original_text)
    if not result["deliverables"]:
        result["deliverables"] = ["Agree on the final deliverables with the client before work begins."]
    if not result["questions"]:
        result["questions"] = make_questions(original_text, "", "")
    if not result["risks"]:
        result["risks"] = make_risks(original_text, "", "")
    if not result["boundaries"]:
        result["boundaries"] = make_boundaries()
    if not result["acceptance_criteria"]:
        result["acceptance_criteria"] = make_acceptance_criteria()
    if not result["client_summary"]:
        result["client_summary"] = make_client_summary(result)
    if not result["suggested_next_step"]:
        result["suggested_next_step"] = "Send the summary to the client and confirm the open questions before estimating the work."
    return result


def derive_title(text: str) -> str:
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    candidate = lines[0] if lines else text.strip()
    candidate = re.sub(r"\s+", " ", candidate)
    if len(candidate) > 72:
        candidate = candidate[:69].rsplit(" ", 1)[0] + "..."
    return candidate or "Untitled client brief"


def sentence_parts(text: str) -> list[str]:
    raw_parts = re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z0-9])", text)
    out = []
    seen = set()
    for part in raw_parts:
        part = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", part).strip()
        part = re.sub(r"\s+", " ", part)
        if len(part) >= 14 and part.lower() not in seen:
            out.append(part)
            seen.add(part.lower())
    return out


def summarize_text(text: str) -> str:
    parts = sentence_parts(text)
    if not parts:
        return "The client has provided an initial project request. More detail is needed to confirm the exact scope and expected outcome."
    summary = " ".join(parts[:2])
    return summary[:650]


def extract_requirements(text: str) -> list[str]:
    parts = sentence_parts(text)
    if not parts:
        return ["Clarify the client's main objective and the exact work requested."]
    action_words = re.compile(r"\b(need|needs|want|wants|must|should|include|create|build|design|develop|add|remove|support|integrate|deliver|provide|make|allow|feature|page|section|system|website|app|application|deadline|budget|revision|mobile|responsive|payment|booking|form|login|dashboard|report)\b", re.I)
    selected = [part for part in parts if action_words.search(part)]
    if not selected:
        selected = parts
    return selected[:7]


def make_questions(text: str, budget: str, deadline: str) -> list[str]:
    lower = text.lower()
    questions = []
    if not budget.strip() and not re.search(r"\b(\$|usd|eur|gbp|pkr|budget|price|cost|rate|payment)\b", lower):
        questions.append("What budget range has been allocated to this project?")
    if not deadline.strip() and not re.search(r"\b(by|deadline|due date|within \d+|week|month|launch date|deliver by)\b", lower):
        questions.append("When does the client need the first review and the final delivery?")
    if not re.search(r"\b(reference|example|inspiration|brand guide|assets|content|copy|images|logo|source files)\b", lower):
        questions.append("Will the client provide existing content, brand assets, references, or source files?")
    if not re.search(r"\b(approve|approval|review|revision|feedback|sign[- ]?off|acceptance)\b", lower):
        questions.append("Who will review the work, and how many revision rounds should be included?")
    if not re.search(r"\b(success|goal|objective|conversion|target|measure|deliverable|final file|handover)\b", lower):
        questions.append("What would make the client consider this project successful?")
    questions.append("Are any integrations, paid tools, ongoing maintenance, or third-party costs expected?")
    return questions[:6]


def make_risks(text: str, budget: str, deadline: str) -> list[dict[str, str]]:
    lower = text.lower()
    risks = []
    if len(text.split()) < 45:
        risks.append({"title": "Brief has limited detail", "detail": "Several decisions may still be assumptions. Confirm the intended outcome and concrete deliverables before quoting a fixed price.", "level": "High"})
    if not deadline.strip() and not re.search(r"\b(deadline|due date|by \w+|within \d+|launch date)\b", lower):
        risks.append({"title": "Timeline is not confirmed", "detail": "Without review dates and a final deadline, delivery expectations can drift. Agree on milestones and client response times.", "level": "Medium"})
    if not budget.strip() and not re.search(r"\b(\$|usd|eur|gbp|pkr|budget|price|cost|rate)\b", lower):
        risks.append({"title": "Budget is unknown", "detail": "A fixed quote is difficult to justify until the client confirms a budget range and any paid third-party costs.", "level": "Medium"})
    if not re.search(r"\b(revision|feedback|approval|approve|sign[- ]?off)\b", lower):
        risks.append({"title": "Feedback process is undefined", "detail": "Unbounded feedback can create extra work. Define who approves the work and how revisions will be handled.", "level": "Medium"})
    if re.search(r"\b(all|everything|full|complete|entire)\b", lower) and len(text.split()) < 120:
        risks.append({"title": "Scope may be broader than the brief", "detail": "Broad words can hide multiple deliverables. Turn them into a written checklist before agreeing to timing or price.", "level": "High"})
    if not risks:
        risks.append({"title": "Dependencies should be confirmed", "detail": "Ask who supplies required access, assets, feedback, and approvals so work is not blocked later.", "level": "Low"})
    return risks[:5]


def make_boundaries() -> list[str]:
    return [
        "Only the deliverables explicitly approved in the final brief are included.",
        "Additional features or new requirements should be estimated and approved separately.",
        "Third-party subscriptions, hosting, stock assets, and other external costs should be agreed separately.",
        "Post-launch support and ongoing maintenance are excluded unless specifically agreed.",
    ]


def make_acceptance_criteria() -> list[str]:
    return [
        "Each deliverable can be checked against the written requirements agreed by both sides.",
        "The client has a defined review window and a named person responsible for approval.",
        "Any known technical, format, or device requirements are tested before handover.",
    ]


def make_client_summary(result: dict[str, Any]) -> str:
    requirements = result.get("requirements", [])[:4]
    checklist = "\n".join(f"- {item}" for item in requirements) if requirements else "- Confirm the main requirements and deliverables"
    return (
        f"Thanks for sharing the project details. My understanding is that the goal is: {result.get('summary', '').strip()}\n\n"
        f"The main points I have captured are:\n{checklist}\n\n"
        "Before I confirm the scope, timeline, and price, I'd like to clarify the open questions below. Once those are agreed, I can send a final scope and delivery plan."
    )


def local_analysis(text: str, project_type: str, budget: str = "", deadline: str = "") -> dict[str, Any]:
    requirements = extract_requirements(text)
    summary = summarize_text(text)
    title = derive_title(text)
    project_label = project_type if project_type and project_type != "Other" else "project"
    goals = [summary]
    if len(requirements) > 1:
        goals.append(f"Deliver the agreed {project_label} in a way that can be reviewed against clear requirements.")
    result = {
        "title": title,
        "summary": summary,
        "goals": goals[:4],
        "requirements": requirements,
        "deliverables": [
            "A written scope listing the agreed outputs and constraints.",
            "The specific assets, files, pages, or functionality described in the confirmed requirements.",
            "A review-ready version for client feedback and approval.",
            "Final handover in the formats agreed with the client.",
        ],
        "questions": make_questions(text, budget, deadline),
        "risks": make_risks(text, budget, deadline),
        "boundaries": make_boundaries(),
        "acceptance_criteria": make_acceptance_criteria(),
        "client_summary": "",
        "suggested_next_step": "Send the open questions to the client. Confirm the deliverables, timeline, review process, and boundaries before committing to a fixed quote.",
    }
    result["client_summary"] = make_client_summary(result)
    return normalize_analysis(result, text)


def analyze_with_gemini(text: str, project_type: str, budget: str, deadline: str, api_key: str, model: str = MODEL_DEFAULT) -> dict[str, Any]:
    prompt = f"""You are ScopeNote, a careful project scoping assistant for freelancers and small teams.
Analyze this client request and turn it into a practical project brief. Do not invent facts. Distinguish stated requirements from assumptions. Keep every item specific, useful, and readable. Ask questions when critical details are missing. Boundaries are proposals to confirm, not claims that the client already agreed.

Project type: {project_type or 'Not specified'}
Budget context supplied by user: {budget or 'Not specified'}
Deadline context supplied by user: {deadline or 'Not specified'}

Return ONLY valid JSON with these exact keys and types:
{{
  "title": "string",
  "summary": "string",
  "goals": ["string"],
  "requirements": ["string"],
  "deliverables": ["string"],
  "questions": ["string"],
  "risks": [{{"title": "string", "detail": "string", "level": "Low|Medium|High"}}],
  "boundaries": ["string"],
  "acceptance_criteria": ["string"],
  "client_summary": "string, ready to send to the client for confirmation",
  "suggested_next_step": "string"
}}
Use 2-5 goals, 3-8 requirements, 3-6 deliverables, 3-7 important questions, 2-5 risks, 3-5 boundaries, and 3-5 acceptance criteria. Do not give legal advice. Do not promise costs or delivery dates. Keep the client_summary professional and concise.

CLIENT REQUEST:
{text}
"""
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = requests.post(
        endpoint,
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.25, "responseMimeType": "application/json"},
        },
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Gemini API returned HTTP {response.status_code}. Check your API key, model name, and API access.")
    payload = response.json()
    try:
        generated = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini returned an empty or unexpected response.") from exc
    generated = generated.strip()
    generated = re.sub(r"^```(?:json)?\s*|\s*```$", "", generated, flags=re.I)
    try:
        data = json.loads(generated)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini response could not be parsed as JSON. Try again or use local mode.") from exc
    return normalize_analysis(data, text)


def analyze_request(text: str, project_type: str, budget: str, deadline: str, api_key: str, model: str = MODEL_DEFAULT) -> tuple[dict[str, Any], str, str | None]:
    if api_key:
        try:
            return analyze_with_gemini(text, project_type, budget, deadline, api_key, model), "Gemini", None
        except (requests.RequestException, RuntimeError, ValueError, KeyError) as exc:
            return local_analysis(text, project_type, budget, deadline), "Local fallback", str(exc)
    return local_analysis(text, project_type, budget, deadline), "Local rules", None
