# Classroom Control MVP (estilo Veyon) - Python

Monorepo proposto:

- `server/`: API FastAPI + dashboard web.
- `agent/`: agente do aluno (console e service Windows).
- `web/`: assets JS/CSS do painel.
- `shared/`: contratos de protocolo e modelos compartilhados.

## Rodando local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
pip install -r agent/requirements.txt
uvicorn server.app.main:app --reload --host 0.0.0.0 --port 8000
```

Em outro terminal:

```bash
python agent/agent.py --device-id pc-lab-01
python agent/agent.py --device-id pc-lab-02
```

Acesse o painel web em `http://127.0.0.1:8000`.

## Instalação como serviço no Windows

```powershell
# Empacotar
pyinstaller --onefile agent/agent.py --name classroom-agent

# Instalar serviço (com Python + pywin32)
python agent/service.py install
python agent/service.py start
```

## Segurança MVP

- TLS obrigatório em produção (`https://`).
- Token por agente no provisionamento inicial.
- Auditoria em memória na rota `/audit-logs`.

## Limitações do MVP

- Persistência em memória (reiniciar servidor perde estado).
- Sem mTLS completo ainda (planejado fase 2).
- Bloqueio HTTP/HTTPS por porta (contornável por VPN/DoH/portas alternativas).
