"""
Session Recorder (TRANSCRIPT-ONLY)
==================================
Saves ONLY the full transcript (both sides) to local files.
No audio recording.

Output structure:
  recordings/
    <customer>_<session>_<timestamp>/
      transcript.json
      metadata.json   (optional)
"""

from __future__ import annotations

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
    ):
        self.session_id = session_id
        self.customer_id = customer_id
        self.user_name = user_name
        self.agent_name = agent_name
        self.language = language
        self.save_metadata = save_metadata

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = RECORDINGS_DIR / f"{customer_id}_{session_id}_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._transcript: list[TranscriptEntry] = []
        self._started_at = datetime.now()

        logger.info(f"📝 Transcript recorder ready → {self.output_dir}")

    # ── Session-level: capture transcript ───────────────────────────────────

    def attach_to_session(self, session) -> None:
        """Hook into AgentSession events to capture the conversation transcript."""

        @session.on("user_input_transcribed")
        def _on_user_speech(ev):
            # Only store final segments to avoid partial duplicates
            if getattr(ev, "is_final", False):
                text = (getattr(ev, "transcript", None) or "").strip()
                if not text:
                    return
                self._transcript.append(
                    TranscriptEntry(
                        role="user",
                        text=text,
                        timestamp=datetime.now().isoformat(),
                    )
                )
                logger.debug(f"📝 User: {text[:120]}")

        @session.on("agent_speech_committed")
        def _on_agent_speech(ev):
            # Different SDKs sometimes shape this differently
            text = ""
            if hasattr(ev, "content") and isinstance(ev.content, str):
                text = ev.content
            else:
                text = str(ev)

            text = (text or "").strip()
            if not text:
                return

            self._transcript.append(
                TranscriptEntry(
                    role="agent",
                    text=text,
                    timestamp=datetime.now().isoformat(),
                )
            )
            logger.debug(f"📝 Agent: {text[:120]}")

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