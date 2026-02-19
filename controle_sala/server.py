"""Servidor de gestão de sala para controlar acesso à internet dos clientes.

Uso:
    uvicorn server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class InternetState(str, Enum):
    LIBERADA = "liberada"
    BLOQUEADA = "bloqueada"


class ClientStatus(BaseModel):
    client_id: str = Field(min_length=3)
    hostname: str
    user_name: str
    ip_address: str
    screenshot_enabled: bool = False
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CommandResponse(BaseModel):
    internet_state: InternetState
    request_screenshot: bool = False
    updated_at: datetime


class ScreenshotPayload(BaseModel):
    client_id: str
    image_b64: str = Field(min_length=20)


class ClientControl(BaseModel):
    internet_state: InternetState = InternetState.LIBERADA
    request_screenshot: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


app = FastAPI(title="Controle de Sala", version="1.0.0")

clients: Dict[str, ClientStatus] = {}
controls: Dict[str, ClientControl] = {}
screenshots: Dict[str, ScreenshotPayload] = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "clients_online": len(clients)}


@app.post("/clients/register", response_model=ClientControl)
def register_client(payload: ClientStatus) -> ClientControl:
    payload.last_seen = datetime.now(timezone.utc)
    clients[payload.client_id] = payload
    controls.setdefault(payload.client_id, ClientControl())
    return controls[payload.client_id]


@app.post("/clients/{client_id}/heartbeat", response_model=CommandResponse)
def heartbeat(client_id: str, payload: ClientStatus) -> CommandResponse:
    if client_id not in clients:
        raise HTTPException(status_code=404, detail="Cliente não registrado")

    payload.last_seen = datetime.now(timezone.utc)
    clients[client_id] = payload

    control = controls.setdefault(client_id, ClientControl())
    response = CommandResponse(
        internet_state=control.internet_state,
        request_screenshot=control.request_screenshot,
        updated_at=control.updated_at,
    )

    if control.request_screenshot:
        control.request_screenshot = False
        control.updated_at = datetime.now(timezone.utc)

    return response


@app.get("/teacher/clients", response_model=List[ClientStatus])
def list_clients() -> List[ClientStatus]:
    return sorted(clients.values(), key=lambda item: item.last_seen, reverse=True)


@app.put("/teacher/clients/{client_id}/internet/{state}", response_model=ClientControl)
def set_internet_state(client_id: str, state: InternetState) -> ClientControl:
    if client_id not in clients:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    control = controls.setdefault(client_id, ClientControl())
    control.internet_state = state
    control.updated_at = datetime.now(timezone.utc)
    return control


@app.post("/teacher/clients/{client_id}/request-screenshot", response_model=ClientControl)
def request_screenshot(client_id: str) -> ClientControl:
    if client_id not in clients:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    control = controls.setdefault(client_id, ClientControl())
    control.request_screenshot = True
    control.updated_at = datetime.now(timezone.utc)
    return control


@app.post("/clients/{client_id}/screenshot")
def upload_screenshot(client_id: str, payload: ScreenshotPayload) -> dict:
    if client_id != payload.client_id:
        raise HTTPException(status_code=400, detail="client_id do caminho difere do payload")

    screenshots[client_id] = payload
    return {"status": "recebido", "capturado_em": datetime.now(timezone.utc)}


@app.get("/teacher/clients/{client_id}/screenshot", response_model=ScreenshotPayload)
def get_latest_screenshot(client_id: str) -> ScreenshotPayload:
    image = screenshots.get(client_id)
    if not image:
        raise HTTPException(status_code=404, detail="Screenshot não disponível")
    return image
