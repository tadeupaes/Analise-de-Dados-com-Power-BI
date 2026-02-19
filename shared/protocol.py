from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


PROTOCOL_VERSION = "1.0"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class InternetPolicyMode(str, Enum):
    OPEN = "open"
    BLOCK_HTTP_HTTPS = "block_http_https"


class AgentRegisterRequest(BaseModel):
    protocol_version: str = PROTOCOL_VERSION
    device_id: str = Field(min_length=3)
    hostname: str
    username: str
    local_ip: str
    mac_address: str | None = None
    os_name: str
    agent_version: str = "0.1.0"


class AgentHeartbeatRequest(BaseModel):
    protocol_version: str = PROTOCOL_VERSION
    device_id: str
    hostname: str
    username: str
    local_ip: str


class ScreenshotUploadRequest(BaseModel):
    protocol_version: str = PROTOCOL_VERSION
    request_id: str
    device_id: str
    image_b64: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CommandMessage(BaseModel):
    protocol_version: str = PROTOCOL_VERSION
    command_id: str
    type: Literal["screenshot.capture", "policy.internet", "file.push"]
    payload: dict[str, Any] = Field(default_factory=dict)
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CommandAck(BaseModel):
    protocol_version: str = PROTOCOL_VERSION
    command_id: str
    device_id: str
    success: bool
    detail: str | None = None
