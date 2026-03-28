#!/usr/bin/env python
"""
Lisa Voice Agent - Run Script
=============================
Starts ONLY the API server.

Usage:
    Terminal 1 (API):      python run.py
    Terminal 2 (Agent):    python -m agent.main dev
    Terminal 3 (Frontend): npm run dev
"""

import uvicorn


def main():
    print()
    print("=" * 60)
    print("🎙️  LISA VOICE AGENT — API SERVER")
    print("=" * 60)
    print()

    try:
        from app.config import Config

        status = Config.get_status()
        print("📋 Configuration:")
        print(f"   LiveKit:  {'✅' if status['livekit'] else '❌ NOT SET'}")
        print(f"   xAI:      {'✅' if status['xai'] else '❌ NOT SET'}")
        print()

        if not status["livekit"]:
            print("⚠️  LiveKit not configured — sessions will be MOCK only!")
            print()
        if not status["xai"]:
            print("⚠️  xAI not configured — agent won't work!")
            print()
    except Exception as e:
        print(f"⚠️  Could not load config: {e}")
        print()

    print("⚠️  Also run the agent:  python -m agent.main dev")
    print()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=Config.PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
