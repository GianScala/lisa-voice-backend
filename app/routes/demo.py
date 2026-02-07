"""
Lisa Voice Agent — Demo Routes
================================
Session creation + LiveKit token generation.
Frontend sends: name, customer_id, language.
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import Config

_root = str(Path(__file__).resolve().parents[2])
if _root not in sys.path:
    sys.path.insert(0, _root)

from customers.store import customer_store

logger = logging.getLogger("api.demo")
router = APIRouter(prefix="/api/demo", tags=["demo"])


# -- Models ------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    name: str
    customer_id: str = "demo"
    language: str = "en"              # ← from frontend language selector


class SessionResponse(BaseModel):
    session_id: str
    room_name: str
    token: str
    livekit_url: str
    customer_name: str
    agent_name: str
    agent_type: str
    language: str
    mode: str


class ConfigStatusResponse(BaseModel):
    livekit: bool
    xai: bool
    ready: bool
    message: str


# -- Sessions -----------------------------------------------------------------

sessions: dict = {}


# -- Endpoints ----------------------------------------------------------------

@router.get("/config")
async def get_config_status() -> ConfigStatusResponse:
    status = Config.get_status()
    ready = status["livekit"] and status["xai"]
    if ready:
        message = "Ready!"
    else:
        missing = [k for k, v in status.items() if not v]
        message = f"Missing: {', '.join(missing)}"
    return ConfigStatusResponse(**status, ready=ready, message=message)


@router.post("/session", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a session. Frontend sends customer_id + language.
    Both get embedded in LiveKit participant metadata so the
    agent worker knows which persona AND language to use.
    """
    logger.info(
        f"🆕 Session — user={request.name}, "
        f"customer={request.customer_id}, lang={request.language}"
    )

    customer = customer_store.get(request.customer_id)
    if not customer:
        raise HTTPException(404, f"Customer '{request.customer_id}' not found")

    session_id = str(uuid.uuid4())[:8]
    room_name = f"{request.customer_id}-{session_id}"

    # ── Metadata the agent will read ──────────────────────────────────
    metadata = json.dumps({
        "name": request.name,
        "customer_id": request.customer_id,
        "language": request.language,          # ← passed to agent
        "session_id": session_id,
    })

    if not Config.is_livekit_configured():
        logger.warning("⚠️ LiveKit not configured — mock session")
        sessions[session_id] = {
            "id": session_id, "room": room_name,
            "user_name": request.name, "customer_id": request.customer_id,
            "language": request.language, "status": "mock",
            "created_at": datetime.utcnow().isoformat(),
        }
        return SessionResponse(
            session_id=session_id, room_name=room_name,
            token="mock-token", livekit_url="wss://not-configured",
            customer_name=customer.name, agent_name=customer.agent_name,
            agent_type=customer.agent_type, language=request.language,
            mode="mock",
        )

    try:
        from livekit.api import AccessToken, VideoGrants

        token = (
            AccessToken(
                api_key=Config.LIVEKIT_API_KEY,
                api_secret=Config.LIVEKIT_API_SECRET,
            )
            .with_identity(f"user-{session_id}")
            .with_name(request.name)
            .with_metadata(metadata)
            .with_grants(
                VideoGrants(
                    room_join=True, room=room_name,
                    can_publish=True, can_subscribe=True,
                )
            )
        )
        jwt_token = token.to_jwt()
    except ImportError:
        raise HTTPException(503, "livekit-api not installed")
    except Exception as e:
        logger.error(f"❌ Token error: {e}", exc_info=True)
        raise HTTPException(500, str(e))

    sessions[session_id] = {
        "id": session_id, "room": room_name,
        "user_name": request.name, "customer_id": request.customer_id,
        "language": request.language, "status": "created",
        "created_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        f"✅ Session {session_id} — room={room_name}, "
        f"agent={customer.agent_name}, lang={request.language}"
    )

    return SessionResponse(
        session_id=session_id, room_name=room_name,
        token=jwt_token, livekit_url=Config.LIVEKIT_URL,
        customer_name=customer.name, agent_name=customer.agent_name,
        agent_type=customer.agent_type, language=request.language,
        mode="live",
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@router.post("/session/{session_id}/end")
async def end_session(session_id: str):
    if session_id in sessions:
        sessions[session_id]["status"] = "ended"
        sessions[session_id]["ended_at"] = datetime.utcnow().isoformat()
    return {"status": "ended", "session_id": session_id}


@router.get("/sessions")
async def list_sessions():
    return {"count": len(sessions), "sessions": list(sessions.values())}