# Deploy — private website (you + friends)

This runs the app at a normal `https://…` URL, gated by a shared password so only
people you give it to can use it (the Anthropic key spends real money, so don't
leave it open).

## What the environment variables do

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | Anthropic key. Set as a platform **secret**, never in the repo. |
| `APP_PASSWORD` | yes (for a public URL) | Shared password gate. If unset, there is **no** gate (local dev only). |
| `DATA_DIR` | yes (deploy) | Where profiles + SQLite live. Point a persistent volume here (the Docker image defaults to `/data`). |
| `STOCKFISH_PATH` | no | Defaults to `/usr/games/stockfish` in the image. |
| `ANTHROPIC_MODEL` | no | Override the model (default `claude-opus-4-6`). |

## Run locally with Docker

```bash
docker build -t chess-profiler .
docker run -p 8501:8501 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e APP_PASSWORD=choose-a-password \
  -v chess_data:/data \
  chess-profiler
# → http://localhost:8501
```

Or `docker compose up` (see `docker-compose.yml`; put the key in a local `.env`).

## Deploy to a URL (Render — simplest)

1. Push this repo to GitHub.
2. Render → **New → Web Service** → connect the repo → it detects the `Dockerfile`.
3. **Environment:** add `ANTHROPIC_API_KEY` (secret) and `APP_PASSWORD`.
4. **Disks:** add a persistent disk mounted at **`/data`** (1 GB is plenty). The image
   already sets `DATA_DIR=/data`.
5. Deploy. You get `https://your-app.onrender.com`. Share that URL + the password
   with your friends.

Fly.io / Railway work the same way: Docker image + one env secret + a volume at `/data`.

## Notes / limitations

- **The password gate is a single shared secret**, not per-user accounts — fine for a
  trusted handful, not for the open internet.
- Picking a tiny instance is okay; analyses are CPU-bound (Stockfish). One or two people
  analyzing at once is fine. If several run simultaneously expect them to be slower.
- Profiles are keyed by chess.com nickname. If two friends analyze the **same** nickname,
  the second overwrites the first — use the delete + profile selector to manage.
- Free tiers that sleep/restart will keep your data **only** because it's on the `/data`
  volume. Without a persistent disk, profiles are wiped on every redeploy.
