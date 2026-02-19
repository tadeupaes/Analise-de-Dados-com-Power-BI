"""Cliente (agente) para receber comandos do servidor de sala.

AVISO: execute apenas em máquinas da escola com autorização.

Uso:
    python client.py --server http://IP_DO_SERVIDOR:8000 --client-id pc-lab-01
"""

from __future__ import annotations

import argparse
import base64
import getpass
import io
import os
import platform
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

import requests
from PIL import ImageGrab


@dataclass
class AgentConfig:
    server: str
    client_id: str
    poll_interval: int = 5
    screenshot_enabled: bool = True
    dry_run_firewall: bool = True


def machine_ip() -> str:
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "0.0.0.0"


def build_status(config: AgentConfig) -> dict:
    return {
        "client_id": config.client_id,
        "hostname": platform.node(),
        "user_name": getpass.getuser(),
        "ip_address": machine_ip(),
        "screenshot_enabled": config.screenshot_enabled,
    }


def run_cmd(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True)


def set_windows_firewall_block(enabled: bool, dry_run: bool = True) -> None:
    """Bloqueia/libera tráfego TCP nas portas 80 e 443 para saída no Windows."""
    if platform.system().lower() != "windows":
        print("[WARN] Regras de firewall implementadas apenas para Windows.")
        return

    rule_name = "Aula_Bloqueio_Web_80_443"

    if enabled:
        command = [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={rule_name}",
            "dir=out",
            "action=block",
            "protocol=TCP",
            "remoteport=80,443",
        ]
    else:
        command = [
            "netsh",
            "advfirewall",
            "firewall",
            "delete",
            "rule",
            f"name={rule_name}",
        ]

    if dry_run:
        print("[DRY-RUN]", " ".join(command))
        return

    run_cmd(command)
    print("[OK] Firewall atualizado", "(bloqueado)" if enabled else "(liberado)")


def capture_screenshot_b64() -> Optional[str]:
    try:
        img = ImageGrab.grab()
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=55)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Falha ao capturar screenshot: {exc}")
        return None


def register(config: AgentConfig) -> None:
    response = requests.post(
        f"{config.server}/clients/register",
        json=build_status(config),
        timeout=10,
    )
    response.raise_for_status()


def send_heartbeat(config: AgentConfig) -> dict:
    response = requests.post(
        f"{config.server}/clients/{config.client_id}/heartbeat",
        json=build_status(config),
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def upload_screenshot(config: AgentConfig, image_b64: str) -> None:
    payload = {"client_id": config.client_id, "image_b64": image_b64}
    response = requests.post(
        f"{config.server}/clients/{config.client_id}/screenshot",
        json=payload,
        timeout=20,
    )
    response.raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente cliente para controle de sala")
    parser.add_argument("--server", required=True, help="Ex: http://192.168.1.10:8000")
    parser.add_argument("--client-id", default=platform.node())
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--disable-screenshot", action="store_true")
    parser.add_argument(
        "--apply-firewall",
        action="store_true",
        help="Aplica de verdade as regras no firewall (sem dry-run)",
    )
    args = parser.parse_args()

    config = AgentConfig(
        server=args.server.rstrip("/"),
        client_id=args.client_id,
        poll_interval=max(2, args.poll_interval),
        screenshot_enabled=not args.disable_screenshot,
        dry_run_firewall=not args.apply_firewall,
    )

    register(config)
    print(f"[INIT] Cliente registrado: {config.client_id}")

    internet_blocked = False

    while True:
        try:
            command = send_heartbeat(config)
            target_blocked = command.get("internet_state") == "bloqueada"

            if target_blocked != internet_blocked:
                set_windows_firewall_block(
                    enabled=target_blocked,
                    dry_run=config.dry_run_firewall,
                )
                internet_blocked = target_blocked

            if command.get("request_screenshot") and config.screenshot_enabled:
                image_b64 = capture_screenshot_b64()
                if image_b64:
                    upload_screenshot(config, image_b64)
                    print("[OK] Screenshot enviado")

        except requests.RequestException as exc:
            print(f"[WARN] Erro de conexão: {exc}")
        except subprocess.CalledProcessError as exc:
            print(f"[WARN] Falha no firewall: {exc}")

        time.sleep(config.poll_interval)


if __name__ == "__main__":
    if os.name == "nt":
        print("[INFO] Rodando em Windows")
    main()
