"""
Persona Registry
=================
Auto-discovers all persona files in this folder.
Each persona file exports a PERSONA dict.

To add a new agent: just create a new .py file here with a PERSONA dict.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("agent.personas")

# All loaded personas: { "demo": {...}, "dental": {...} }
_registry: Dict[str, dict] = {}


def _discover() -> None:
    """Import every module in this package and register its PERSONA."""
    package_dir = Path(__file__).parent
    for finder, name, _ in pkgutil.iter_modules([str(package_dir)]):
        if name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f".{name}", package=__package__)
            persona = getattr(module, "PERSONA", None)
            if persona and isinstance(persona, dict) and "id" in persona:
                _registry[persona["id"]] = persona
                logger.info(f"  Loaded persona: {persona['id']} → {persona['agent_name']}")
        except Exception as e:
            logger.warning(f"  Failed to load persona '{name}': {e}")


def get(persona_id: str) -> Optional[dict]:
    """Get a persona by ID."""
    if not _registry:
        _discover()
    return _registry.get(persona_id)


def get_all() -> Dict[str, dict]:
    """Get all registered personas."""
    if not _registry:
        _discover()
    return dict(_registry)


# Auto-discover on import
_discover()