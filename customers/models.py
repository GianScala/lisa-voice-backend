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
    agent_name: str = "Assistant"
    agent_type: str = "general_business"
    voice: str = "eve"
    language: str = "en"

    system_prompt: str = ""
    intro_message: str = (
        "Hi, this is {agent_name}, helping with {business_name}. "
        "I can help get this taken care of quickly. What do you need help with today?"
    )
    goodbye_message: str = (
        "Perfect — I've got everything I need. We'll follow up as soon as possible. Thanks for calling."
    )

    business_category: Optional[str] = None
    service_area: Optional[str] = None
    business_hours: Optional[str] = None
    business_address: Optional[str] = None
    services: List[str] = field(default_factory=list)
    common_customer_questions: List[str] = field(default_factory=list)
    booking_link_enabled: bool = False
    booking_link_url: Optional[str] = None

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def get_full_system_prompt(self) -> str:
        parts = [self.system_prompt] if self.system_prompt else [
            f"You are {self.agent_name}, helping with {self.name}. "
            "You sound like a real front-desk assistant who moves the situation forward."
        ]
        parts.append(
            "Handle missed calls like an active small-business assistant: start with a reassuring opening, "
            "understand the problem quickly, gather the details needed to act, and make the caller feel "
            "their request is already being handled."
        )
        parts.append(
            "Never sound like voicemail. Do not say the owner is unavailable, do not ask the caller to leave a message, "
            "and do not mention AI."
        )
        parts.append(
            "Use active phrasing like: 'I'll help get this handled quickly,' 'Let me grab a couple details so we can take care of this,' "
            "and 'I'll make sure the team gets this right away.'"
        )
        if self.business_category:
            parts.append(f"Business category: {self.business_category}.")
        if self.services:
            parts.append(f"Services: {', '.join(self.services)}.")
        if self.service_area:
            parts.append(f"Service area: {self.service_area}.")
        if self.business_hours:
            parts.append(f"Hours: {self.business_hours}.")
        if self.business_address:
            parts.append(f"Address: {self.business_address}.")
        if self.common_customer_questions:
            parts.append(
                f"Common customer questions: {', '.join(self.common_customer_questions)}."
            )
        if self.booking_link_enabled and self.booking_link_url:
            parts.append(
                "Booking link available after collecting details: "
                f"{self.booking_link_url}."
            )
        return "\n\n".join(parts)

    def get_intro(self, user_name: Optional[str] = None) -> str:
        return self.intro_message.format(
            user_name=user_name or "there",
            agent_name=self.agent_name,
            business_name=self.name,
        )

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "voice": self.voice,
            "language": self.language,
            "business_category": self.business_category,
            "service_area": self.service_area,
            "booking_link_enabled": self.booking_link_enabled,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }
