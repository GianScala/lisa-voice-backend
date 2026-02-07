"""
Lisa Voice Agent — Customer Store
===================================
Reads agent personas from agent/personas/*.py files.
Those files are the SINGLE SOURCE OF TRUTH.

This store wraps them in CustomerConfig objects for the API routes.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .models import CustomerConfig

# Ensure we can import agent.personas
_root = str(Path(__file__).resolve().parents[1])
if _root not in sys.path:
    sys.path.insert(0, _root)

from agent.personas import get_all as get_all_personas

logger = logging.getLogger("customers.store")


class CustomerStore:
    def __init__(self) -> None:
        self._customers: Dict[str, CustomerConfig] = {}
        self._load_from_personas()

    def _load_from_personas(self) -> None:
        """Import all personas and convert to CustomerConfig objects."""
        for pid, persona in get_all_personas().items():
            self._customers[pid] = CustomerConfig(
                id=persona["id"],
                name=persona["name"],
                agent_name=persona["agent_name"],
                agent_type=persona.get("agent_type", "lisa"),
                voice=persona.get("voice", "eve"),
                language=persona.get("language", "en"),
                system_prompt=persona.get("system_prompt", ""),
                intro_message=persona.get("intro_message", "Hello!"),
                goodbye_message=persona.get("goodbye_message", "Goodbye!"),
                business_hours=persona.get("business_hours"),
                business_address=persona.get("business_address"),
                services=persona.get("services", []),
            )
        logger.info(f"Loaded {len(self._customers)} customers from persona files")

    # -- CRUD (create/update/delete for runtime additions via API) -----

    def get(self, customer_id: str) -> Optional[CustomerConfig]:
        return self._customers.get(customer_id)

    def list_all(self) -> List[CustomerConfig]:
        return list(self._customers.values())

    def list_active(self) -> List[CustomerConfig]:
        return [c for c in self._customers.values() if c.is_active]

    def create(self, customer: CustomerConfig) -> CustomerConfig:
        self._customers[customer.id] = customer
        return customer

    def update(self, customer_id: str, updates: dict) -> Optional[CustomerConfig]:
        customer = self._customers.get(customer_id)
        if not customer:
            return None
        for k, v in updates.items():
            if hasattr(customer, k):
                setattr(customer, k, v)
        return customer

    def delete(self, customer_id: str) -> bool:
        return self._customers.pop(customer_id, None) is not None


# Singleton
customer_store = CustomerStore()