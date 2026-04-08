"""
Session Recorder (TRANSCRIPT-ONLY)
==================================
Saves ONLY the full transcript (both sides) to local files.
Also publishes transcript entries to the LiveKit room data channel
so the frontend can display them in real time.

Output structure:
  recordings/
    <customer>_<session>_<timestamp>/
      transcript.json
      metadata.json   (optional)
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("agent.recorder")

# Where transcripts are saved
RECORDINGS_DIR = Path(__file__).resolve().parents[1] / "recordings"


@dataclass
class TranscriptEntry:
    role: str          # "user" | "agent"
    text: str
    timestamp: str     # ISO-8601


class SessionRecorder:
    """Transcript-only recorder for a single voice conversation session."""

    def __init__(
        self,
        session_id: str,
        customer_id: str,
        user_name: str,
        agent_name: str,
        language: str = "en",
        save_metadata: bool = True,
        room=None,
    ):
        self.session_id = session_id
        self.customer_id = customer_id
        self.user_name = user_name
        self.agent_name = agent_name
        self.language = language
        self.save_metadata = save_metadata
        self.room = room

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = RECORDINGS_DIR / f"{customer_id}_{session_id}_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._transcript: list[TranscriptEntry] = []
        self._started_at = datetime.now()

        logger.info(f"📝 Transcript recorder ready → {self.output_dir}")

    # ── Publish transcript entry to LiveKit data channel ──────────────────

    def _publish_to_room(self, role: str, text: str, action: str = "add") -> None:
        """Publish a transcript entry to the LiveKit room so the frontend can display it."""
        if not self.room:
            return
        try:
            payload = json.dumps({
                "type": "transcript",
                "role": role,
                "text": text,
                "action": action,
                "timestamp": datetime.now().isoformat(),
            }).encode("utf-8")
            loop = asyncio.get_running_loop()
            loop.create_task(
                self.room.local_participant.publish_data(payload, reliable=True)
            )
        except Exception:
            logger.debug("Could not publish transcript to data channel", exc_info=True)

    def _last_entry_by_role(self, role: str) -> TranscriptEntry | None:
        for entry in reversed(self._transcript):
            if entry.role == role:
                return entry
        return None

    # ── Session-level: capture transcript ───────────────────────────────────

    def attach_to_session(self, session) -> None:
        """Hook into AgentSession events to capture the conversation transcript."""

        @session.on("user_input_transcribed")
        def _on_user_speech(ev):
            if not getattr(ev, "is_final", False):
                return
            text = (getattr(ev, "transcript", None) or "").strip()
            if not text:
                return

            # Deduplicate: if new text is a superset of the last user entry,
            # replace it instead of adding a new one (STT sends incremental finals)
            last = self._last_entry_by_role("user")
            if last and (text.startswith(last.text) or last.text.startswith(text)):
                last.text = text
                last.timestamp = datetime.now().isoformat()
                self._publish_to_room("user", text, action="replace")
                logger.debug(f"📝 User (updated): {text[:120]}")
            else:
                self._transcript.append(
                    TranscriptEntry(
                        role="user",
                        text=text,
                        timestamp=datetime.now().isoformat(),
                    )
                )
                self._publish_to_room("user", text, action="add")
                logger.debug(f"📝 User: {text[:120]}")

        @session.on("conversation_item_added")
        def _on_conversation_item(ev):
            message = ev.item
            role = getattr(message, "role", None)
            logger.info(f"📨 conversation_item_added: role={role}")

            if role != "assistant":
                return

            text = self._extract_text(message)
            if text:
                self._add_agent_entry(text)

        def _debug_events(name: str):
            """Register a catch-all debug listener."""
            @session.on(name)
            def _handler(ev):
                logger.info(f"🔍 Event '{name}': {type(ev).__name__} — {str(ev)[:200]}")

        # Register debug listeners for agent-related events
        for evt in ("agent_state_changed", "speech_created"):
            _debug_events(evt)

    def _extract_text(self, message) -> str:
        """Extract text from a ChatMessage, handling various content formats."""
        # Try text_content property first
        if hasattr(message, "text_content"):
            text = message.text_content or ""
            if text.strip():
                return text.strip()

        # Try iterating content items for text or audio transcript
        if hasattr(message, "content") and hasattr(message.content, "__iter__"):
            parts = []
            for item in message.content:
                if hasattr(item, "text") and item.text:
                    parts.append(item.text)
                elif hasattr(item, "transcript") and item.transcript:
                    parts.append(item.transcript)
            if parts:
                return " ".join(parts).strip()

        # Try content as string
        if hasattr(message, "content") and isinstance(message.content, str):
            text = message.content.strip()
            if text:
                return text

        return ""

    def _add_agent_entry(self, text: str) -> None:
        """Add an agent transcript entry, deduplicating if needed."""
        last = self._last_entry_by_role("agent")
        if last and last.text == text:
            return  # exact duplicate, skip

        self._transcript.append(
            TranscriptEntry(
                role="agent",
                text=text,
                timestamp=datetime.now().isoformat(),
            )
        )
        self._publish_to_room("agent", text, action="add")
        logger.info(f"📝 Agent: {text[:120]}")

    # ── Save transcript (and optional metadata) ─────────────────────────────

    async def save(self) -> dict:
        """
        Save transcript to disk. Call this when the session ends.
        Returns a summary dict of saved file paths.
        """
        saved_files: dict[str, str] = {}

        # 1) Save transcript
        transcript_path = self.output_dir / "transcript.json"
        transcript_payload = [
            {"role": e.role, "text": e.text, "timestamp": e.timestamp}
            for e in self._transcript
        ]
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(transcript_payload, f, indent=2, ensure_ascii=False)

        saved_files["transcript"] = str(transcript_path)
        logger.info(f"💾 Transcript: {transcript_path} ({len(self._transcript)} entries)")

        # 2) Save metadata (optional)
        if self.save_metadata:
            ended_at = datetime.now()
            metadata = {
                "session_id": self.session_id,
                "customer_id": self.customer_id,
                "user_name": self.user_name,
                "agent_name": self.agent_name,
                "language": self.language,
                "started_at": self._started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
                "duration_seconds": (ended_at - self._started_at).total_seconds(),
                "transcript_entries": len(self._transcript),
            }
            metadata_path = self.output_dir / "metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            saved_files["metadata"] = str(metadata_path)
            logger.info(f"💾 Metadata: {metadata_path}")

        logger.info(f"✅ Transcript saved → {self.output_dir}")
        return saved_files