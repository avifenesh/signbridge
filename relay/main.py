"""
SignBridge Bot Relay — Path B fallback server.

Joins Telegram group calls via pytgcalls, streams raw PCM audio to the
Android app over WebSocket.

Endpoints
---------
POST /session/start   {chat_id}            → {session_id, audio_url}
POST /session/end     {session_id}         → {status}
GET  /sessions                             → [{id, chat_id, state, created_at}]
GET  /audio/{session_id}                   → WebSocket (binary PCM frames)
GET  /health                               → {status: ok}
"""
from __future__ import annotations

import asyncio
import contextlib
import logging

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from bridge import CallBridge
from config import cfg
from session import SessionManager, State

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
log = logging.getLogger("relay")

# ---------------------------------------------------------------------------
# Lifespan — start / stop the Telegram client once
# ---------------------------------------------------------------------------

bridge: CallBridge | None = None
mgr = SessionManager(cfg.max_sessions)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global bridge
    cfg.validate()
    bridge = CallBridge(
        app_id=cfg.telegram_app_id,
        app_hash=cfg.telegram_app_hash,
        phone=cfg.telegram_phone,
        session_file=cfg.session_file,
    )
    await bridge.start()
    log.info("relay ready on %s:%d", cfg.listen_host, cfg.listen_port)
    yield
    await mgr.close_all()
    await bridge.stop()
    log.info("relay shut down")


app = FastAPI(title="SignBridge Relay", lifespan=lifespan)

# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


class StartReq(BaseModel):
    chat_id: int


class StartResp(BaseModel):
    session_id: str
    audio_url: str


class EndReq(BaseModel):
    session_id: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/session/start", response_model=StartResp, status_code=201)
async def session_start(req: StartReq, request: Request):
    try:
        sess = mgr.create(req.chat_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    async def _run():
        try:
            await bridge.join(sess)
        except Exception:
            log.exception("bridge error (session %s)", sess.id)
            sess.stop_event.set()
            mgr.remove(sess.id)

    asyncio.create_task(_run())

    host = request.headers.get("host", "localhost:8080")
    return StartResp(
        session_id=sess.id,
        audio_url=f"ws://{host}/audio/{sess.id}",
    )


@app.post("/session/end")
async def session_end(req: EndReq):
    sess = mgr.get(req.session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="session not found")
    sess.state = State.LEAVING
    sess.stop_event.set()
    mgr.remove(sess.id)
    return {"status": "ended"}


@app.get("/sessions")
async def session_list():
    return [s.to_dict() for s in mgr.list_all()]


# ---------------------------------------------------------------------------
# WebSocket — streams raw PCM audio to the phone
# ---------------------------------------------------------------------------


@app.websocket("/audio/{session_id}")
async def audio_ws(ws: WebSocket, session_id: str):
    sess = mgr.get(session_id)
    if sess is None:
        await ws.close(code=4004, reason="session not found")
        return

    await ws.accept()
    sess.ws = ws
    log.info("audio ws connected (session %s)", session_id)

    try:
        while not sess.stop_event.is_set():
            try:
                frame = await asyncio.wait_for(sess.audio_q.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            await ws.send_bytes(frame)
    except WebSocketDisconnect:
        log.info("audio ws disconnected (session %s)", session_id)
    except Exception:
        log.exception("audio ws error (session %s)", session_id)
    finally:
        sess.ws = None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=cfg.listen_host,
        port=cfg.listen_port,
        log_level="info",
    )
