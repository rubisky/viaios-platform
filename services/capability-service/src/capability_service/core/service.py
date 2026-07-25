"""Capability OS Marketplace — Capability Registry and Model Mesh Router."""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Capability:
    """A registered capability in the marketplace."""

    def __init__(
        self,
        name: str,
        description: str,
        version: str,
        endpoint: str,
        provider: str,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.endpoint = endpoint
        self.provider = provider
        self.input_schema = input_schema or {}
        self.output_schema = output_schema or {}
        self.tags = tags or []
        self.created_at = datetime.now(timezone.utc)
        self.invocation_count = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "endpoint": self.endpoint,
            "provider": self.provider,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "invocation_count": self.invocation_count,
        }


class CapabilityRegistry:
    """Registry of capabilities in the marketplace."""

    def __init__(self):
        self._capabilities: dict[str, Capability] = {}

    def register(
        self,
        name: str,
        description: str,
        version: str,
        endpoint: str,
        provider: str,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Capability:
        if name in self._capabilities:
            raise ValueError(f"Capability already registered: {name}")

        cap = Capability(
            name=name,
            description=description,
            version=version,
            endpoint=endpoint,
            provider=provider,
            input_schema=input_schema,
            output_schema=output_schema,
            tags=tags,
        )
        self._capabilities[name] = cap
        logger.info("Registered capability: %s v%s", name, version)
        return cap

    def list(self, tag: Optional[str] = None) -> list[Capability]:
        capabilities = list(self._capabilities.values())
        if tag:
            capabilities = [c for c in capabilities if tag in c.tags]
        return capabilities

    def get(self, name: str) -> Optional[Capability]:
        return self._capabilities.get(name)

    def invoke(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        capability = self._capabilities.get(name)
        if not capability:
            raise ValueError(f"Capability not found: {name}")

        capability.invocation_count += 1
        logger.info("Invoking capability: %s (count: %d)", name, capability.invocation_count)

        return {
            "capability": name,
            "version": capability.version,
            "provider": capability.provider,
            "input": params,
            "output": {
                "status": "success",
                "message": f"Capability {name} executed successfully",
                "invocation_id": str(uuid.uuid4()),
            },
        }


class ModelMeshRouter:
    """Routes requests to the most appropriate AI model."""

    DEFAULT_MODELS = [
        {"name": "gpt-4o", "provider": "openai", "type": "text", "cost": "high", "latency": "medium"},
        {"name": "gpt-4o-mini", "provider": "openai", "type": "text", "cost": "low", "latency": "low"},
        {"name": "claude-sonnet-4-20250514", "provider": "anthropic", "type": "text", "cost": "medium", "latency": "low"},
        {"name": "gemini-2.5-flash", "provider": "google", "type": "multimodal", "cost": "low", "latency": "low"},
        {"name": "dall-e-3", "provider": "openai", "type": "image", "cost": "high", "latency": "high"},
    ]

    def __init__(self):
        self._models: list[dict[str, str]] = list(self.DEFAULT_MODELS)

    def select_model(
        self,
        task_type: str = "text",
        preferred_provider: Optional[str] = None,
        max_cost: str = "medium",
        max_latency: str = "medium",
    ) -> Optional[Dict[str, str]]:
        """Select the best model based on constraints."""
        candidates = [m for m in self._models if m["type"] == task_type]

        if preferred_provider:
            candidates = [m for m in candidates if m["provider"] == preferred_provider]

        cost_order = {"low": 0, "medium": 1, "high": 2}
        latency_order = {"low": 0, "medium": 1, "high": 2}

        candidates = [
            m for m in candidates
            if cost_order.get(m["cost"], 2) <= cost_order.get(max_cost, 2)
            and latency_order.get(m["latency"], 2) <= latency_order.get(max_latency, 2)
        ]

        if not candidates:
            return None

        # Return lowest cost model among candidates
        candidates.sort(key=lambda m: cost_order.get(m["cost"], 2))
        return candidates[0]

    def list_models(self) -> list[dict[str, str]]:
        return list(self._models)

    def register_model(self, model: dict[str, str]) -> None:
        self._models.append(model)
        logger.info("Registered model: %s", model.get("name"))


# Global instances
capability_registry = CapabilityRegistry()
model_mesh_router = ModelMeshRouter()
