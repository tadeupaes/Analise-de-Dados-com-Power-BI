from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from shared.protocol import DeviceStatus, InternetPolicyMode


@dataclass(slots=True)
class Device:
    device_id: str
    hostname: str
    username: str
    local_ip: str
    mac_address: str | None
    os_name: str
    agent_version: str
    status: DeviceStatus = DeviceStatus.ONLINE
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_policy: InternetPolicyMode = InternetPolicyMode.OPEN


@dataclass(slots=True)
class AuditEntry:
    actor: str
    action: str
    target: str
    detail: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
