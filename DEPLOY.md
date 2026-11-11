# Deploy — site com login e dados persistentes

O app roda numa URL `https://…` normal. Cada pessoa cria a própria conta (usuário +
senha) e vê só as próprias análises. As contas, as sessões de login e as análises
ficam num banco **PostgreSQL** fora do container, então nada se perde em redeploys,
reinícios ou em hospedagens gratuitas sem disco persistente.

## Variáveis de ambiente

| Variável | Obrigatória | Para quê |
|---|---|---|
| `ANTHROPIC_API_KEY` | sim | Chave da Anthropic. Configure como **secret** na plataforma, nunca no repositório. |
| `DATABASE_URL` | sim (deploy) | URL do Postgres: `postgresql://usuario:senha@host:5432/banco?sslmode=require`. Sem ela, o app usa o SQLite local (só serve para desenvolvimento). |
| `SIGNUP_CODE` | recomendada | Código de convite exigido para criar conta. Sem ele (e sem `APP_PASSWORD`), qualquer visitante pode se cadastrar e gastar sua chave da API. |
| `ALLOW_SIGNUP` | não | `0` fecha o cadastro pela interface; contas passam a ser criadas com `python manage.py create-user`. |
| `SESSION_TTL_DAYS` | não | Por quantos dias o login fica lembrado no navegador (padrão 30). |
| `DATA_DIR` | não | Onde fica o cache do Stockfish (SQLite, regenerável). A imagem usa `/data`. |
| `STOCKFISH_PATH` | não | Padrão `/usr/games/stockfish` na imagem. |
| `ANTHROPIC_MODEL` | não | Troca o modelo (padrão `claude-opus-4-6`). |
| `APP_PASSWORD` | legado | A antiga senha compartilhada; agora vale como `SIGNUP_CODE` se este não estiver definido. |

## Banco Postgres gratuito

Qualquer Postgres serve. Opções sem custo para começar:

- **Neon** (neon.tech) → crie um projeto → copie a *connection string* (já vem com `sslmode=require`).
- **Supabase** → Project Settings → Database → *Connection string* (URI). Prefira a do *Session pooler*.
- **Render Postgres** → New → PostgreSQL → *Internal Database URL* (se o app também estiver no Render).

As tabelas são criadas automaticamente na primeira conexão.

## Rodar localmente com Docker (app + Postgres)

```bash
docker compose up --build
# → http://localhost:8501
```

O `docker-compose.yml` sobe um Postgres com volume próprio (`pg_data`). Coloque
`ANTHROPIC_API_KEY` (e opcionalmente `SIGNUP_CODE`) num `.env` local.

## Deploy numa URL (Render)

1. Faça push deste repositório para o GitHub.
2. Crie o banco (Neon/Supabase/Render Postgres) e copie a URL.
3. Render → **New → Web Service** → conecte o repositório → ele detecta o `Dockerfile`.
4. **Environment:** `ANTHROPIC_API_KEY` (secret), `DATABASE_URL` (secret) e `SIGNUP_CODE`.
5. Deploy. Abra a URL, vá em **Criar conta** e crie a sua: **a primeira conta vira
   administradora** e recebe as análises que existiam antes do login.
6. Passe a URL e o código de convite para os amigos.

Fly.io / Railway funcionam igual: imagem Docker + secrets. Disco persistente não é mais
necessário (o `/data` guarda só o cache do Stockfish).

## Administração (`manage.py`)

Rode no shell do serviço (ou localmente com o mesmo `DATABASE_URL`):

```bash
python manage.py info                       # qual banco está em uso, nº de contas/análises
python manage.py list-users
python manage.py create-user ana            # pede a senha
python manage.py set-password ana           # redefine a senha (esqueceu) e encerra as sessões
python manage.py delete-user ana            # apaga a conta e as análises dela
python manage.py purge-sessions             # limpa sessões expiradas
```

### Levar análises antigas para o Postgres

Análises feitas antes (no SQLite local `data/profiler.db`) podem ser copiadas para o
banco do deploy e atribuídas a uma conta:

```bash
DATABASE_URL=postgresql://... python manage.py import-sqlite data/profiler.db --owner ana
```

## Segurança — o que foi feito e os limites

- Senhas guardadas com PBKDF2-HMAC-SHA256 (600 mil iterações, salt por usuário); nunca em texto.
- Login lembrado por um cookie com token aleatório; o banco guarda só o SHA-256 do token.
  Sair, trocar a senha ou redefinir a senha invalida as sessões no servidor.
- 5 senhas erradas seguidas bloqueiam a conta por 15 minutos.
- O cookie é gravado via JavaScript (o Streamlit não grava cookies pelo servidor), então
  não é `HttpOnly`; é `SameSite=Strict` e `Secure` em HTTPS.
- Não há recuperação de senha por e-mail: o administrador redefine com `manage.py set-password`.
- Análises são CPU-bound (Stockfish). Uma ou duas pessoas analisando ao mesmo tempo é ok;
  mais que isso fica lento numa instância pequena.
