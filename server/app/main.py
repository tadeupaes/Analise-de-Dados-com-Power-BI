from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from shared.models import AuditEntry, Device
from shared.protocol import (
    AgentHeartbeatRequest,
    AgentRegisterRequest,
    CommandAck,
    CommandMessage,
    DeviceStatus,
    InternetPolicyMode,
    ScreenshotUploadRequest,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("classroom-server")

BASE_DIR = Path(__file__).resolve().parents[2]
app = FastAPI(title="Classroom Control MVP", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "web"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "server" / "templates"))

DEVICES: dict[str, Device] = {}
AGENT_SOCKETS: dict[str, WebSocket] = {}
PENDING_COMMANDS: dict[str, list[CommandMessage]] = defaultdict(list)
SCREENSHOTS: dict[str, ScreenshotUploadRequest] = {}
AUDIT_LOGS: list[AuditEntry] = []


@app.on_event("startup")
async def startup_event() -> None:
    asyncio.create_task(_mark_offline_loop())


async def _mark_offline_loop() -> None:
    while True:
        now = datetime.now(timezone.utc)
        for device in DEVICES.values():
            if now - device.last_seen > timedelta(seconds=25):
                device.status = DeviceStatus.OFFLINE
        await asyncio.sleep(5)


def _audit(action: str, target: str, detail: str, actor: str = "teacher") -> None:
    AUDIT_LOGS.append(AuditEntry(actor=actor, action=action, target=target, detail=detail))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/agents/register")
async def register_agent(payload: AgentRegisterRequest) -> dict[str, str]:
    DEVICES[payload.device_id] = Device(
        device_id=payload.device_id,
        hostname=payload.hostname,
        username=payload.username,
        local_ip=payload.local_ip,
        mac_address=payload.mac_address,
        os_name=payload.os_name,
        agent_version=payload.agent_version,
        status=DeviceStatus.ONLINE,
    )
    _audit("agent.register", payload.device_id, f"host={payload.hostname}", actor="agent")
    return {"status": "registered", "device_id": payload.device_id}


@app.post("/agents/heartbeat")
async def heartbeat(payload: AgentHeartbeatRequest) -> dict[str, str]:
    device = DEVICES.get(payload.device_id)
    if not device:
        raise HTTPException(status_code=404, detail="device not registered")
    device.hostname = payload.hostname
    device.username = payload.username
    device.local_ip = payload.local_ip
    device.last_seen = datetime.now(timezone.utc)
    device.status = DeviceStatus.ONLINE
    return {"status": "ok"}


@app.websocket("/ws/agent/{device_id}")
async def agent_ws(ws: WebSocket, device_id: str) -> None:
    await ws.accept()
    AGENT_SOCKETS[device_id] = ws
    logger.info("agent connected %s", device_id)
    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            if data.get("type") == "ack":
                ack = CommandAck.model_validate(data["payload"])
                _audit("command.ack", ack.device_id, f"{ack.command_id} success={ack.success}", actor="agent")
            elif data.get("type") == "screenshot.upload":
                shot = ScreenshotUploadRequest.model_validate(data["payload"])
                SCREENSHOTS[shot.device_id] = shot
                _audit("screenshot.upload", shot.device_id, shot.request_id, actor="agent")
    except WebSocketDisconnect:
        logger.info("agent disconnected %s", device_id)
    finally:
        AGENT_SOCKETS.pop(device_id, None)


@app.get("/devices")
async def list_devices() -> list[dict[str, Any]]:
    return [
        {
            "device_id": d.device_id,
            "hostname": d.hostname,
            "username": d.username,
            "local_ip": d.local_ip,
            "status": d.status,
            "last_seen": d.last_seen,
            "current_policy": d.current_policy,
        }
        for d in DEVICES.values()
    ]


@app.post("/screenshots/request")
async def request_screenshot(device_ids: list[str]) -> dict[str, Any]:
    created: list[str] = []
    for device_id in device_ids:
        if device_id not in DEVICES:
            continue
        command = CommandMessage(
            command_id=str(uuid4()),
            type="screenshot.capture",
            payload={"quality": 55},
        )
        PENDING_COMMANDS[device_id].append(command)
        created.append(device_id)
        _audit("screenshot.request", device_id, command.command_id)
    return {"requested": created}


@app.post("/policies/apply")
async def apply_policy(payload: dict[str, Any]) -> dict[str, Any]:
    mode = InternetPolicyMode(payload.get("mode", InternetPolicyMode.OPEN))
    device_ids = payload.get("device_ids", [])
    for device_id in device_ids:
        if device_id not in DEVICES:
            continue
        DEVICES[device_id].current_policy = mode
        command = CommandMessage(
            command_id=str(uuid4()),
            type="policy.internet",
            payload={"mode": mode},
        )
        PENDING_COMMANDS[device_id].append(command)
        _audit("policy.apply", device_id, f"mode={mode}")
    return {"status": "ok"}


@app.get("/agents/{device_id}/commands")
async def pull_commands(device_id: str) -> dict[str, Any]:
    queue = PENDING_COMMANDS[device_id]
    PENDING_COMMANDS[device_id] = []
    return {"commands": [c.model_dump(mode="json") for c in queue]}


@app.get("/screenshots/{device_id}")
async def get_screenshot(device_id: str) -> dict[str, Any]:
    shot = SCREENSHOTS.get(device_id)
    if not shot:
        raise HTTPException(status_code=404, detail="screenshot not found")
    return shot.model_dump(mode="json")


@app.get("/audit-logs")
async def list_audit() -> list[dict[str, Any]]:
    return [
        {
            "actor": a.actor,
            "action": a.action,
            "target": a.target,
            "detail": a.detail,
            "created_at": a.created_at,
        }
        for a in AUDIT_LOGS[-500:]
    ]
