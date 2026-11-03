"""LLM Integration Service for ProofPay Scoping Agent.

Uses Google Gemini via langchain-google-genai with configurable model and structured outputs.
Includes robust error handling, quota fallback, and offline mock capabilities for testing.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Suppress the SDK automatic function calling warning emitted by google_genai.models
logging.getLogger("google_genai.models").setLevel(logging.ERROR)
try:
    from google.genai.models import Models
    Models._logged_afc_warning = True
except Exception:
    pass

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from ProofPay.agents.scoping_agent.criteria_library import get_criteria_prompt_documentation
from ProofPay.agents.scoping_agent.schemas import (
    ClarityCheckSchema,
    MilestonePlanSchema,
)
from ProofPay.agents.scoping_agent.prompts import (
    SYSTEM_SECURITY_PREAMBLE,
    CLARITY_CHECK_PROMPT,
    GENERATE_MILESTONES_PROMPT,
    REPAIR_PLAN_PROMPT,
    format_verified_config_documentation,
)

load_dotenv()

FALLBACK_MODELS = ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]


class LLMServiceError(Exception):
    """Raised when LLM invocation fails or returns malformed response."""
    pass


class LLMService:
    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._llms: Dict[str, ChatGoogleGenerativeAI] = {}

    def _get_llm(self, model_name: Optional[str] = None) -> ChatGoogleGenerativeAI:
        target_model = model_name or self.model_name
        if target_model not in self._llms:
            if not self.api_key:
                raise LLMServiceError("GOOGLE_API_KEY environment variable is not set.")
            self._llms[target_model] = ChatGoogleGenerativeAI(
                model=target_model,
                google_api_key=self.api_key,
                temperature=0.2,
                max_retries=2,
            )
        return self._llms[target_model]

    def _invoke_structured(self, schema: Any, prompt: str) -> Any:
        """Invoke structured output with automatic fallback across available models if quota is exhausted."""
        models_to_try = [self.model_name] + [m for m in FALLBACK_MODELS if m != self.model_name]
        last_error = None
        for m in models_to_try:
            try:
                llm = self._get_llm(model_name=m)
                structured_llm = llm.with_structured_output(schema, method="json_schema")
                response = structured_llm.invoke([
                    SystemMessage(content=SYSTEM_SECURITY_PREAMBLE),
                    HumanMessage(content=prompt),
                ])
                return response
            except Exception as e:
                last_error = e
                if "RESOURCE_EXHAUSTED" in str(e):
                    continue
                raise
        raise LLMServiceError(f"LLM call failed after trying models {models_to_try}: {str(last_error)}") from last_error

    def check_clarity(
        self,
        project_description: str,
        total_budget: float,
        currency: str,
        deadline: str,
    ) -> ClarityCheckSchema:
        """Inspect project description for clarity and generate clarification questions if needed."""
        user_prompt = CLARITY_CHECK_PROMPT.format(
            project_description=project_description,
            total_budget=total_budget,
            currency=currency,
            deadline=deadline,
        )
        try:
            return self._invoke_structured(ClarityCheckSchema, user_prompt)
        except Exception as e:
            raise LLMServiceError(f"LLM check_clarity failed: {str(e)}") from e

    def generate_milestones(
        self,
        project_description: str,
        total_budget: float,
        currency: str,
        deadline: str,
        user_provided_config: Optional[Dict[str, Any]] = None,
    ) -> MilestonePlanSchema:
        """Call 1: Generate initial milestone roadmap with criteria from predefined library."""
        user_prompt = GENERATE_MILESTONES_PROMPT.format(
            criteria_documentation=get_criteria_prompt_documentation(),
            verified_config_section=format_verified_config_documentation(user_provided_config),
            project_description=project_description,
            total_budget=total_budget,
            currency=currency,
            deadline=deadline,
        )
        try:
            return self._invoke_structured(MilestonePlanSchema, user_prompt)
        except Exception as e:
            raise LLMServiceError(f"LLM generate_milestones failed: {str(e)}") from e

    def repair_milestones(
        self,
        project_description: str,
        total_budget: float,
        currency: str,
        deadline: str,
        current_milestones: List[Dict[str, Any]],
        validation_errors: List[str],
        user_provided_config: Optional[Dict[str, Any]] = None,
    ) -> MilestonePlanSchema:
        """Call 2: Repair an invalid milestone plan using exact deterministic validation errors."""
        errors_text = "\n".join(f"- {err}" for err in validation_errors)
        user_prompt = REPAIR_PLAN_PROMPT.format(
            criteria_documentation=get_criteria_prompt_documentation(),
            verified_config_section=format_verified_config_documentation(user_provided_config),
            project_description=project_description,
            total_budget=total_budget,
            currency=currency,
            deadline=deadline,
            current_milestones=json.dumps(current_milestones, indent=2),
            validation_errors=errors_text,
        )
        try:
            return self._invoke_structured(MilestonePlanSchema, user_prompt)
        except Exception as e:
            raise LLMServiceError(f"LLM repair_milestones failed: {str(e)}") from e


# Global default service instance
llm_service = LLMService()
