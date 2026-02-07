"""
Lisa Voice Agent — Customer Model
===================================
Data shape for agent personas.
Used by the API routes to serialize/deserialize.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class CustomerConfig:
    name: str
    agent_name: str = "Lisa"
    agent_type: str = "lisa"
    voice: str = "eve"
    language: str = "en"

    system_prompt: str = ""
    intro_message: str = "Hello {user_name}! I'm {agent_name}. How can I help?"
    goodbye_message: str = "Goodbye! Have a great day."

    business_hours: Optional[str] = None
    business_address: Optional[str] = None
    services: List[str] = field(default_factory=list)

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def get_full_system_prompt(self) -> str:
        parts = [self.system_prompt] if self.system_prompt else [
            f"You are {self.agent_name}, a helpful voice assistant for {self.name}."
        ]
        if self.services:
            parts.append(f"Services: {', '.join(self.services)}.")
        if self.business_hours:
            parts.append(f"Hours: {self.business_hours}.")
        if self.business_address:
            parts.append(f"Address: {self.business_address}.")
        return "\n\n".join(parts)

    def get_intro(self, user_name: Optional[str] = None) -> str:
        return self.intro_message.format(
            user_name=user_name or "there",
            agent_name=self.agent_name,
        )

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "voice": self.voice,
            "language": self.language,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }