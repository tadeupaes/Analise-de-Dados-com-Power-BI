# Controle de Sala (Servidor + Cliente)

> Projeto educacional para laboratório escolar. Use **somente** com autorização institucional e transparência para os alunos.

## O que este protótipo faz

- Servidor HTTP para registrar máquinas clientes e guardar estado de controle.
- Cliente Python que:
  - envia heartbeat;
  - recebe comando para **bloquear/liberar internet** (portas 80 e 443 no Windows);
  - envia screenshot quando o professor solicitar.
- CLI de professor para listar máquinas e enviar comandos.

## Arquitetura

- `server.py`: API FastAPI com rotas de cliente e professor.
- `client.py`: agente nas máquinas dos alunos.
- `teacher_cli.py`: comando para o professor operar.

## Instalação

```bash
cd controle_sala
python -m venv .venv
source .venv/bin/activate  # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 1) Subir servidor

```bash
cd controle_sala
uvicorn server:app --host 0.0.0.0 --port 8000
```

## 2) Rodar cliente (aluno)

```bash
cd controle_sala
python client.py --server http://IP_DO_SERVIDOR:8000 --client-id pc-lab-01
```

### Modo seguro (padrão)

Por padrão, o cliente roda com `dry-run` de firewall (apenas imprime os comandos sem aplicar):

```bash
python client.py --server http://IP_DO_SERVIDOR:8000 --client-id pc-lab-01
```

Para aplicar no firewall real (Windows com privilégio de administrador):

```bash
python client.py --server http://IP_DO_SERVIDOR:8000 --client-id pc-lab-01 --apply-firewall
```

## 3) Comandos do professor

Listar clientes:

```bash
python teacher_cli.py --server http://IP_DO_SERVIDOR:8000 list
```

Bloquear internet de um cliente:

```bash
python teacher_cli.py --server http://IP_DO_SERVIDOR:8000 block pc-lab-01
```

Liberar internet:

```bash
python teacher_cli.py --server http://IP_DO_SERVIDOR:8000 unblock pc-lab-01
```

Solicitar screenshot:

```bash
python teacher_cli.py --server http://IP_DO_SERVIDOR:8000 request-shot pc-lab-01
```

Baixar último screenshot (em JSON com base64):

```bash
python teacher_cli.py --server http://IP_DO_SERVIDOR:8000 get-shot pc-lab-01 --output screenshot_payload.json
```

## Observações importantes

- O bloqueio de portas foi implementado para **Windows** com `netsh advfirewall`.
- Em Linux/macOS, adapte a função para `iptables`/`pf`.
- Para produção, adicione autenticação, TLS, logs e criptografia dos screenshots.
