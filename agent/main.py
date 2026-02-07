"""
Lisa Voice Agent — Agent Worker (TRANSCRIPT-ONLY)
=================================================
Uses xAI Grok Voice Agent API (speech-to-speech).
Loads persona from agent/personas/*.py, reads language from frontend metadata.
Saves ONLY the full transcript to recordings/ folder (no audio recording).

Run with:
    python -m agent.main dev
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession
from livekit.plugins import xai

_root = str(Path(__file__).resolve().parents[1])
if _root not in sys.path:
    sys.path.insert(0, _root)

from agent.personas import get as get_persona, get_all as get_all_personas
from agent.recorder import SessionRecorder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lisa-agent")


# =============================================================================
# Language mapping
# =============================================================================
LANGUAGE_NAMES = {
    "en": "English", "it": "Italian", "es": "Spanish", "fr": "French",
    "de": "German", "pt": "Portuguese", "nl": "Dutch", "ja": "Japanese",
    "ko": "Korean", "zh": "Chinese", "ar": "Arabic", "hi": "Hindi",
    "ru": "Russian", "vi": "Vietnamese", "th": "Thai", "tr": "Turkish",
}


def get_language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


# =============================================================================
# Build prompts
# =============================================================================
def build_system_prompt(persona: dict, language: str) -> str:
    parts = []
    if language != "en":
        lang_name = get_language_name(language)
        parts.append(
            f"CRITICAL LANGUAGE RULE: You MUST speak and respond ONLY in {lang_name}. "
            f"All your spoken output must be in {lang_name}. "
            f"Never switch to English unless the user explicitly asks you to."
        )
    parts.append(persona["system_prompt"])

    if services := persona.get("services"):
        parts.append(f"Services offered: {', '.join(services)}.")
    if hours := persona.get("business_hours"):
        parts.append(f"Business hours: {hours}.")
    if address := persona.get("business_address"):
        parts.append(f"Located at: {address}.")

    return "\n\n".join(parts)


def build_intro_instruction(persona: dict, user_name: str, language: str) -> str:
    base_intro = persona["intro_message"].format(
        user_name=user_name, agent_name=persona["agent_name"]
    )
    if language == "en":
        return f"Greet the user by saying: {base_intro}"
    lang_name = get_language_name(language)
    return (
        f'Greet the user in {lang_name}. Translate this greeting naturally into '
        f'{lang_name}: "{base_intro}"'
    )


# =============================================================================
# Helper: wait for remote participant
# =============================================================================
async def wait_for_first_remote_participant(room, timeout_s: float = 15.0):
    """
    Wait until at least one remote participant exists.
    Avoids firing the intro before there is anyone to speak to.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while loop.time() < deadline:
        if room.remote_participants:
            return next(iter(room.remote_participants.values()))
        await asyncio.sleep(0.05)
    return None


# =============================================================================
# Server
# =============================================================================
server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    logger.info("🔌 Connecting to room...")
    await ctx.connect()

    # ── Wait for a user to join ──────────────────────────────────────────────
    first_p = await wait_for_first_remote_participant(ctx.room, timeout_s=15.0)
    if first_p:
        logger.info(f"👤 Remote participant joined: {first_p.identity}")
    else:
        logger.warning("⚠️ No remote participant joined within 15s; continuing anyway.")

    # ── Read metadata ───────────────────────────────────────────────────────
    customer_id = "demo"
    user_name = "there"
    session_id = "unknown"
    language = "en"

    candidates = []
    if first_p:
        candidates.append(first_p)
    candidates.extend(ctx.room.remote_participants.values())

    for p in candidates:
        if getattr(p, "metadata", None):
            try:
                meta = json.loads(p.metadata)
                customer_id = meta.get("customer_id", "demo")
                user_name = meta.get("name", "there")
                session_id = meta.get("session_id", "unknown")
                language = meta.get("language", "en")
            except Exception:
                logger.exception("Failed to parse participant metadata")
            break

    logger.info(f"📋 customer={customer_id}, user={user_name}, session={session_id}, lang={language}")

    # ── Load persona ────────────────────────────────────────────────────────
    persona = get_persona(customer_id) or get_persona("demo")
    voice = persona["voice"]
    agent_name = persona["agent_name"]
    instructions = build_system_prompt(persona, language)

    logger.info(f"🤖 {agent_name} | voice={voice} | lang={get_language_name(language)}")

    # ── Create agent ────────────────────────────────────────────────────────
    agent = Agent(
        instructions=instructions,
        llm=xai.realtime.RealtimeModel(voice=voice),
    )

    # ── Recorder (TRANSCRIPT ONLY) ──────────────────────────────────────────
    recorder = SessionRecorder(
        session_id=session_id,
        customer_id=customer_id,
        user_name=user_name,
        agent_name=agent_name,
        language=language,
        save_metadata=True,   # set False if you want transcript only
    )

    # ── Start session ───────────────────────────────────────────────────────
    session = AgentSession()
    recorder.attach_to_session(session)
    await session.start(room=ctx.room, agent=agent)
    logger.info(f"✅ {agent_name} is live! ({get_language_name(language)})")

    await asyncio.sleep(0)

    # ── Greeting ────────────────────────────────────────────────────────────
    if not ctx.room.remote_participants:
        logger.info("⏳ Waiting briefly for participant before greeting...")
        await wait_for_first_remote_participant(ctx.room, timeout_s=5.0)

    if ctx.room.remote_participants:
        intro_instruction = build_intro_instruction(persona, user_name, language)
        logger.info("👋 Sending intro message...")
        await session.generate_reply(instructions=intro_instruction)
    else:
        logger.warning("⚠️ Still no remote participants; cannot deliver intro.")

    # ── Save transcript on disconnect ───────────────────────────────────────
    async def _save_transcript():
        try:
            logger.info("🛑 Session ended — saving transcript...")
            saved = await recorder.save()
            logger.info(f"💾 Saved: {list(saved.keys())}")
        except Exception:
            logger.exception("Failed while saving transcript")

    @session.on("close")
    def _on_close():
        # LiveKit requires sync callback here
        try:
            asyncio.get_running_loop().create_task(_save_transcript())
        except RuntimeError:
            logger.warning("No running event loop during close; skipping save task")


# =============================================================================
# CLI
# =============================================================================
if __name__ == "__main__":
    personas = get_all_personas()
    logger.info(f"📋 {len(personas)} personas loaded: {list(personas.keys())}")
    for pid, p in personas.items():
        logger.info(f"  {pid}: {p['agent_name']} (voice={p['voice']})")

    agents.cli.run_app(server)