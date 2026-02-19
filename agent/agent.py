from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import logging
import os
import platform
import socket
import subprocess
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
import mss
import websockets
from PIL import Image

from shared.protocol import CommandAck, InternetPolicyMode

LOGGER = logging.getLogger("classroom-agent")


@dataclass(slots=True)
class AgentConfig:
    server_http: str
    server_ws: str
    device_id: str
    token: str
    heartbeat_s: int = 5


def local_ip() -> str:
    return socket.gethostbyname(socket.gethostname())


def capture_screenshot_b64(quality: int = 55) -> str:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def apply_windows_policy(mode: InternetPolicyMode) -> None:
    prefix = "CLASSROOMCTRL_"
    clear = [
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={prefix}BLOCK80"],
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={prefix}BLOCK443"],
    ]
    for cmd in clear:
        subprocess.run(cmd, capture_output=True, text=True, check=False)

    if mode == InternetPolicyMode.BLOCK_HTTP_HTTPS and os.name == "nt":
        rules = [
            ["netsh", "advfirewall", "firewall", "add", "rule", f"name={prefix}BLOCK80", "dir=out", "action=block", "protocol=TCP", "remoteport=80"],
            ["netsh", "advfirewall", "firewall", "add", "rule", f"name={prefix}BLOCK443", "dir=out", "action=block", "protocol=TCP", "remoteport=443"],
        ]
        for cmd in rules:
            subprocess.run(cmd, capture_output=True, text=True, check=True)


async def register(config: AgentConfig) -> None:
    payload = {
        "device_id": config.device_id,
        "hostname": platform.node(),
        "username": os.getenv("USERNAME", "student"),
        "local_ip": local_ip(),
        "mac_address": str(uuid.getnode()),
        "os_name": platform.platform(),
        "agent_version": "0.1.0",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(f"{config.server_http}/agents/register", json=payload)
        response.raise_for_status()


async def heartbeat_loop(config: AgentConfig) -> None:
    while True:
        payload = {
            "device_id": config.device_id,
            "hostname": platform.node(),
            "username": os.getenv("USERNAME", "student"),
            "local_ip": local_ip(),
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{config.server_http}/agents/heartbeat", json=payload)
                response.raise_for_status()

                commands = await client.get(f"{config.server_http}/agents/{config.device_id}/commands")
                commands.raise_for_status()
                for cmd in commands.json().get("commands", []):
                    await execute_command(config, cmd)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("heartbeat failed: %s", exc)

        await asyncio.sleep(config.heartbeat_s)


async def execute_command(config: AgentConfig, command: dict[str, Any]) -> None:
    cmd_type = command.get("type")
    if cmd_type == "policy.internet":
        mode = InternetPolicyMode(command["payload"]["mode"])
        apply_windows_policy(mode)
    elif cmd_type == "screenshot.capture":
        shot = capture_screenshot_b64(quality=command.get("payload", {}).get("quality", 55))
        await send_ws(config, {
            "type": "screenshot.upload",
            "payload": {
                "request_id": command["command_id"],
                "device_id": config.device_id,
                "image_b64": shot,
            },
        })

    ack = CommandAck(command_id=command["command_id"], device_id=config.device_id, success=True)
    await send_ws(config, {"type": "ack", "payload": ack.model_dump(mode="json")})


async def send_ws(config: AgentConfig, payload: dict[str, Any]) -> None:
    uri = f"{config.server_ws}/ws/agent/{config.device_id}?token={config.token}"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps(payload))


async def run(config: AgentConfig) -> None:
    await register(config)
    await heartbeat_loop(config)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-http", default="http://127.0.0.1:8000")
    parser.add_argument("--server-ws", default="ws://127.0.0.1:8000")
    parser.add_argument("--device-id", default=f"pc-{platform.node()}")
    parser.add_argument("--token", default="dev-token")
    args = parser.parse_args()

    config = AgentConfig(args.server_http.rstrip("/"), args.server_ws.rstrip("/"), args.device_id, args.token)
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
