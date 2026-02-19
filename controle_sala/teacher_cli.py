"""CLI do professor para controlar os clientes conectados ao servidor."""

from __future__ import annotations

import argparse
import json

import requests


def list_clients(server: str) -> None:
    response = requests.get(f"{server}/teacher/clients", timeout=10)
    response.raise_for_status()
    clients = response.json()

    if not clients:
        print("Nenhum cliente conectado.")
        return

    for item in clients:
        print(
            f"- {item['client_id']} | host={item['hostname']} | ip={item['ip_address']} | "
            f"último_heartbeat={item['last_seen']}"
        )


def set_internet(server: str, client_id: str, blocked: bool) -> None:
    state = "bloqueada" if blocked else "liberada"
    response = requests.put(
        f"{server}/teacher/clients/{client_id}/internet/{state}",
        timeout=10,
    )
    response.raise_for_status()
    print(f"Internet de {client_id} -> {state}")


def request_screenshot(server: str, client_id: str) -> None:
    response = requests.post(
        f"{server}/teacher/clients/{client_id}/request-screenshot",
        timeout=10,
    )
    response.raise_for_status()
    print(f"Solicitação de screenshot enviada para {client_id}")


def get_screenshot(server: str, client_id: str, output_path: str) -> None:
    response = requests.get(
        f"{server}/teacher/clients/{client_id}/screenshot",
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    with open(output_path, "w", encoding="utf-8") as handler:
        handler.write(json.dumps(payload))
    print(f"Screenshot salvo (base64 em JSON) em {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Painel CLI do professor")
    parser.add_argument("--server", required=True, help="Ex: http://192.168.1.10:8000")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list")

    cmd_block = subparsers.add_parser("block")
    cmd_block.add_argument("client_id")

    cmd_unblock = subparsers.add_parser("unblock")
    cmd_unblock.add_argument("client_id")

    cmd_request = subparsers.add_parser("request-shot")
    cmd_request.add_argument("client_id")

    cmd_get = subparsers.add_parser("get-shot")
    cmd_get.add_argument("client_id")
    cmd_get.add_argument("--output", default="screenshot_payload.json")

    args = parser.parse_args()
    server = args.server.rstrip("/")

    if args.command == "list":
        list_clients(server)
    elif args.command == "block":
        set_internet(server, args.client_id, blocked=True)
    elif args.command == "unblock":
        set_internet(server, args.client_id, blocked=False)
    elif args.command == "request-shot":
        request_screenshot(server, args.client_id)
    elif args.command == "get-shot":
        get_screenshot(server, args.client_id, args.output)


if __name__ == "__main__":
    main()
