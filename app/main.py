"""
Lisa Voice Agent — API Server
===============================
FastAPI app. Start with: python run.py
"""

import logging
import sys
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Config
from .routes import demo, customers

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("lisa-api")
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# App
app = FastAPI(title="Lisa Voice Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(demo.router)
app.include_router(customers.router)


@app.get("/")
async def root():
    return {
        "name": "Lisa Voice Agent API",
        "version": "1.0.0",
        "status": "running",
        "config": Config.get_status(),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "config": "/api/demo/config",
            "create_session": "POST /api/demo/session",
            "customers": "/api/customers",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.on_event("startup")
async def startup():
    status = Config.get_status()
    logger.info("=" * 60)
    logger.info("🎙️  LISA VOICE AGENT API")
    logger.info("=" * 60)
    logger.info(f"   LiveKit: {'✅' if status['livekit'] else '❌'}")
    logger.info(f"   xAI:     {'✅' if status['xai'] else '❌'}")
    logger.info("=" * 60)
    logger.info("⚠️  Also run: python -m agent.main dev")
    logger.info(f"📡 http://localhost:{Config.PORT}")
    logger.info(f"📚 http://localhost:{Config.PORT}/docs")
    logger.info("=" * 60)