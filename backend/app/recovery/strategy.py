"""
Recovery Strategy & Template Rendering Engine.

Determines the next action in the ladder based on diagnosis and attempt count.
Renders localized emails in English and Hindi with strict Jinja2 autoescaping.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import jinja2
import yaml

from backend.app.stubs import audit, llm

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = ROOT / "backend" / "app" / "recovery" / "templates"
STRATEGY_CONFIG = ROOT / "backend" / "app" / "recovery" / "config" / "strategy_table.yaml"

# Setup Jinja2 environment with autoescape enabled
_JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=jinja2.select_autoescape(["html", "jinja2", "xml"]),
)

_STRATEGY_CACHE: dict[str, Any] | None = None


def load_strategy_table() -> dict[str, Any]:
    global _STRATEGY_CACHE
    if _STRATEGY_CACHE is not None:
        return _STRATEGY_CACHE

    if STRATEGY_CONFIG.exists():
        with open(STRATEGY_CONFIG, "r", encoding="utf-8") as f:
            _STRATEGY_CACHE = yaml.safe_load(f) or {}
            return _STRATEGY_CACHE
    return {}


def next_step(
    diagnosis: str,
    attempts: int = 0,
    promised_date: str | None = None,
) -> dict[str, Any]:
    """
    Look up the next action step in the recovery ladder for a given diagnosis and attempt count.
    
    Returns dict with keys:
      - action: e.g. retry_and_reminder, send_payment_link, offer_split_payment, request_card_update, escalate
      - channel: email, payment_link, or none
      - template: template name (e.g. insufficient_funds, payment_link)
      - align_payday: bool
      - step_index: int
    """
    table = load_strategy_table().get("strategies", {})

    # If customer has an active promise-to-pay date
    if promised_date:
        diag_steps = table.get("promised_date", [])
    else:
        diag_steps = table.get(diagnosis, [])

    if not diag_steps:
        # Fallback to forgot_to_pay standard ladder
        diag_steps = table.get("forgot_to_pay", [])

    # If attempts exceeds ladder steps, escalate to human
    if attempts >= len(diag_steps):
        return {
            "action": "escalate",
            "channel": "none",
            "template": "escalate",
            "align_payday": False,
            "step_index": attempts,
            "description": "Exceeded strategy ladder attempts; escalate to human",
        }

    step_info = dict(diag_steps[attempts])
    step_info["step_index"] = attempts
    return step_info


def render_email(
    template_name: str,
    language: str = "en",
    context: dict[str, Any] | None = None,
    case_id: str | None = None,
    allow_llm_customization: bool = False,
) -> str:
    """
    Render email using Jinja2 with autoescaping on.
    Only allows an optional 2nd LLM call if no template exists or if requested,
    safely counted in the budget and falling back to a deterministic template.
    """
    lang = language.lower() if language and language.lower() in ("en", "hi") else "en"
    ctx = context or {}

    # Standard template filename: {lang}/{template_name}.jinja2
    template_rel_path = f"{lang}/{template_name}.jinja2"

    try:
        template = _JINJA_ENV.get_template(template_rel_path)
        return template.render(**ctx)
    except jinja2.TemplateNotFound:
        # Template does not exist for this specific action
        if allow_llm_customization and case_id:
            try:
                # Counted against max 2 LLM calls per case
                llm_prompt = (
                    f"Draft a polite recovery reminder email in language '{lang}' for balance {ctx.get('amount_usd')} {ctx.get('currency', 'USD')}. "
                    "Include an opt-out line: 'To unsubscribe or opt out, reply STOP.'"
                )
                generated_body = llm.complete(case_id, llm_prompt)
                audit.log_event("email_rendered_via_llm_fallback", {
                    "case_id": case_id,
                    "language": lang,
                    "template": template_name,
                })
                return generated_body
            except Exception as e:
                logger.warning("LLM draft fallback failed for case %s: %s", case_id, e)

        # Fallback to forgot_to_pay template
        fallback_path = f"{lang}/forgot_to_pay.jinja2"
        fallback_template = _JINJA_ENV.get_template(fallback_path)
        return fallback_template.render(**ctx)

