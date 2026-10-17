"""Asks Claude to diagnose an alert and return a fix as structured JSON."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = "claude-opus-5-5"

SCHEMA = {
    "type": "object",
    "properties": {
        "diagnosis": {"type": "string", "description": "What is failing and the evidence for it, 2-4 sentences."},
        "root_cause": {"type": "string", "description": "The underlying cause in the shop's code, 1-2 sentences."},
        "fix_summary": {"type": "string", "description": "What the change does, 1-3 sentences."},
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Repo-relative path under site/"},
                    "content": {"type": "string", "description": "Complete new file contents"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
        "commit_message": {"type": "string", "description": "Git commit message: short subject line, blank line, body."},
        "risk": {"type": "string", "description": "What could go wrong with this change, 1-2 sentences."},
        "digest": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "what_happened": {"type": "string"},
                "customer_impact": {"type": "string"},
                "what_we_changed": {"type": "string"},
                "status": {"type": "string"},
            },
            "required": ["headline", "what_happened", "customer_impact", "what_we_changed", "status"],
            "additionalProperties": False,
        },
    },
    "required": ["diagnosis", "root_cause", "fix_summary", "files", "commit_message", "risk", "digest"],
    "additionalProperties": False,
}


def build_prompt(alert, customer_errors, previous_attempt, git_log, files):
    task = (ROOT / "prompts/agent_task.md").read_text()
    file_blocks = "\n\n".join(f'<file path="{p}">\n{c}\n</file>' for p, c in files.items())
    for key, value in {
        "{alert}": json.dumps(alert, indent=2),
        "{customer_errors}": json.dumps(customer_errors, indent=2) if customer_errors else "None reported.",
        "{previous_attempt}": json.dumps(previous_attempt, indent=2) if previous_attempt else "None, this is the first attempt.",
        "{git_log}": git_log,
        "{files}": file_blocks,
    }.items():
        task = task.replace(key, value)
    return task


def diagnose(alert, customer_errors, previous_attempt, git_log, files):
    """Returns (result_dict, meta). Raises on API errors or refusals."""
    import anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=32000,
        # Opus 5.5 defaults to medium effort; set explicitly. Medium keeps the live demo loop under a minute.
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        # If a safety classifier declines, the API retries on a suitable fallback model in the same call.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=(ROOT / "prompts/agent_system.md").read_text(),
        messages=[{"role": "user", "content": build_prompt(alert, customer_errors, previous_attempt, git_log, files)}],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined this request.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Claude's answer was cut off (max_tokens).")
    text = next(b.text for b in response.content if b.type == "text")
    meta = {
        "model": response.model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "rehearsal": False,
    }
    return json.loads(text), meta


def rehearsal_diagnose(alert, customer_errors, previous_attempt, git_log, files):
    """Canned answer so the loop can be rehearsed without an API key. Clearly labelled in the admin panel."""
    canned = json.loads((ROOT / "agent/rehearsal/response.json").read_text())
    canned["files"] = [{"path": "site/cart-client.js", "content": (ROOT / "agent/rehearsal/cart-client.fixed.js").read_text()}]
    return canned, {"model": "rehearsal (no Claude call)", "input_tokens": 0, "output_tokens": 0, "rehearsal": True}


def use_rehearsal():
    return os.environ.get("REHEARSAL") == "1" or not os.environ.get("ANTHROPIC_API_KEY")
