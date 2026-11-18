"""
Fake LLM client for SafeSight AI tests and offline execution.
Deterministic, offline, fast, and requires no external API keys.
"""
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel


class FakeLLMClient:
    """Mock LLM provider for unit tests and local deterministic execution."""

    def __init__(self, provider_name: str = "fake"):
        self.provider_name = provider_name
        self.call_history = []

    @property
    def name(self) -> str:
        return self.provider_name

    def is_available(self) -> bool:
        return True

    def generate(self, system: str, user: str, max_tokens: int = 800) -> str:
        """Returns deterministic mock answers based on input keywords."""
        self.call_history.append({"system": system, "user": user, "max_tokens": max_tokens})
        u_lower = user.lower()

        if "say approved" in u_lower or "ignore previous" in u_lower:
            # Prompt injection defense check
            return "I could not find this in the available documents or events."

        if "weld" in u_lower:
            return "According to [S1], operators must wear shade 10-12 welding helmets with auto-darkening filters, leather jackets, and heat-resistant welding gloves."

        if "goggle" in u_lower or "eye" in u_lower:
            return "Based on [S1], two workers in the cutting area were observed without safety goggles. Under [S2], eye protection complying with ANSI Z87.1 is mandatory."

        if "crane" in u_lower:
            return "According to [S1], subcontractor personnel entered the active crane swing radius without hardhat and steel-toed boots."

        if "not_answerable" in u_lower or "unobtainium" in u_lower:
            return "I could not find this in the available documents or events."

        return "Based on the safety records [S1], standard industrial PPE compliance is mandatory across all active operational zones."

    def generate_json(self, system: str, user: str, schema: Type[BaseModel]) -> Dict[str, Any]:
        """Returns deterministic valid schema-compliant dictionaries."""
        self.call_history.append({"system": system, "user": user, "type": "json"})
        u_lower = user.lower()

        # If schema is for intent classification
        fields = schema.model_fields if hasattr(schema, "model_fields") else {}
        if "intent" in fields:
            if "investigate" in u_lower:
                return {"intent": "start_investigation", "confidence": 0.95, "violation_id": 14}
            elif any(w in u_lower for w in ["how many", "count", "trend", "today", "camera", "stats"]):
                return {"intent": "visual_question", "confidence": 0.90, "violation_id": None}
            elif any(w in u_lower for w in ["manual", "rule", "policy", "sop", "required", "weld"]):
                return {"intent": "document_question", "confidence": 0.92, "violation_id": None}
            elif any(w in u_lower for w in ["weather", "movie", "pizza", "stock"]):
                return {"intent": "out_of_scope", "confidence": 0.99, "violation_id": None}
            else:
                return {"intent": "document_question", "confidence": 0.80, "violation_id": None}

        # Generic default model fallback
        try:
            return schema.model_construct().model_dump()
        except Exception:
            return {}
