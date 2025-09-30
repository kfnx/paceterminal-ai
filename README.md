# PACETERMINAL AI

AI chat API with OpenAI integration.

## Setup

install uv
copy .env.example to .env and fill the keys.

```bash
uv sync
uv run prisma generate
uv run uvicorn main:app --reload
```

## Deploy

```bash
flyctl deploy
```
