# Sistema de Controle de Sala (MVP estilo Veyon)

## 1) Arquitetura geral

Componentes:

- Professor Web UI (browser) -> Server API (FastAPI + templates)
- Server API -> WebSocket endpoint para upload de eventos do agente
- Server API -> HTTP pull de comandos para agentes (`/agents/{id}/commands`)
- Agente Windows (service/console) -> heartbeat/registro + execução de comandos

Fluxo:

1. Agente inicia, registra em `/agents/register`.
2. Agente mantém heartbeat em `/agents/heartbeat`.
3. Professor clica ação no painel, servidor grava comando pendente.
4. Agente busca comandos em `/agents/{id}/commands` e executa.
5. Para screenshot, agente envia payload base64 por WebSocket.
6. Servidor atualiza dashboard e auditoria.

Escolha de protocolo MVP: **HTTP + polling + WebSocket**.

- HTTP polling simplifica operação em LAN escolar.
- WebSocket cobre upload assíncrono (screenshot/ack).
- gRPC fica para fase 2 (maior complexidade operacional no Windows).

## 2) Stack sugerida

- Backend: FastAPI + Uvicorn.
- Banco: SQLite no MVP (neste código está in-memory, pronto para plugar SQLite/PostgreSQL).
- Fila: opcional Redis apenas em escala maior.
- Frontend: HTML + Bootstrap + JS (sem build complexo).
- Screenshot: `mss` + Pillow (JPEG qualidade 55).

## 3) Modelo de dados

Entidades mínimas:

- `devices`: device_id, hostname, username, local_ip, mac_address, os_name, agent_version, status, last_seen, current_policy.
- `classrooms`: id, name.
- `policies`: id, classroom_id, mode, allowlist_json.
- `file_transfers`: id, direction, source, target, sha256, status, bytes_total, bytes_done.
- `audit_logs`: actor, action, target, detail, created_at.
- `users/roles`: id, username, role(admin|teacher), password_hash.

Identificação de máquina: device_id + hostname + MAC + token (fase 2: certificado cliente para mTLS).

## 4) Protocolos e endpoints

- `POST /agents/register`
- `POST /agents/heartbeat`
- `GET /agents/{device_id}/commands`
- `WS /ws/agent/{device_id}`
- `POST /screenshots/request`
- `GET /screenshots/{device_id}`
- `POST /policies/apply`
- `GET /audit-logs`

Versionamento: campo `protocol_version` em todas mensagens JSON.

## 5) Segurança

- MVP: token por agente e TLS obrigatório em produção.
- Evolução recomendada: mTLS com CA escolar.
- Provisionamento: gerar token por instalação e salvar no agente.
- RBAC: `teacher` (opera turma) e `admin` (credenciais/políticas globais).
- Auditoria: ação, alvo, ator, timestamp UTC e resultado.
- Threat model: impedir agente falso, MITM, replay e comando sem permissão.

## 6) Agente Windows Service

Módulos:

- `agent.py`: loop principal, heartbeat e execução de comandos.
- `service.py`: wrapper de serviço usando pywin32.
- firewall: aplicado dentro de `apply_windows_policy`.
- screenshot: `capture_screenshot_b64`.

Instalação:

- `pyinstaller --onefile agent/agent.py --name classroom-agent`
- `python agent/service.py install && python agent/service.py start`

## 7) Bloqueio de internet (Windows)

Implementado com `netsh advfirewall`, prefixo `CLASSROOMCTRL_`.

- Remove regras antigas antes de aplicar novas.
- Bloqueia saída TCP 80 e 443.
- Reversão: remover regras com mesmo prefixo.

Limitações MVP: não cobre VPN, QUIC/443 UDP, proxies e DoH customizado.

## 8) Captura de tela

- Captura full-screen com `mss`.
- Compressão JPEG (qualidade configurável no comando).
- Envio base64 por WebSocket.

## 9) Transferência de arquivos

Estratégia MVP recomendada:

1. Professor envia arquivo ao servidor (`/files/upload`).
2. Servidor cria comando `file.push` com URL temporária.
3. Agente baixa e valida SHA-256.
4. Coleta (`/files/collect`): agente envia entrega por multipart com metadados.

(Endpoints de arquivo ficam para próximo commit.)

## 10) Painel web do professor

Telas MVP implementadas:

- Dashboard com grade de dispositivos e status.
- Ação por dispositivo: solicitar screenshot.
- Ações em lote: aplicar política bloquear/liberar.

Telas planejadas: login, turmas, página detalhada do dispositivo, auditoria avançada.

## 11) Estrutura de pastas

- `server/`
- `agent/`
- `web/`
- `shared/`
- `docs/`

## 12) Código base mínimo funcional

- Registro e heartbeat de agente.
- Pull de comandos.
- Solicitação/retorno de screenshot.
- UI web para listar e acionar screenshot/política.

## 13) Teste e deploy

Teste local:

1. subir servidor;
2. iniciar 2 agentes com ids diferentes;
3. abrir dashboard;
4. solicitar screenshot e bloquear/liberar.

Deploy em laboratório:

- publicar servidor em host interno com TLS;
- instalar agente como service com privilégio admin;
- validar checklist de rede, logs e rollback de firewall.
