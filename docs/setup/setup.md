# Setup Guide

## Project layout

The workshop is split between a frontend app in `code/web` and a Python API in `code/api`:

```text
code
├── api
│   ├── app.py
│   ├── config.py
│   ├── .env
│   ├── .env.example
│   ├── faq_index.py
│   ├── support_service.py
│   ├── support_faqs.json
│   ├── requirements.txt
│   ├── semantic_cache.py
│   └── semantic_router.py
└── web
    ├── index.html
    ├── main.js
    ├── package.json
    ├── style.css
    └── vite.config.js
```

## What each part does

| File | Purpose |
|------|---------|
| `api/app.py` | FastAPI routes for health, research, and cache reset |
| `api/faq_index.py` | Redis FAQ ingestion and vector retrieval |
| `api/semantic_cache.py` | Redis vector search cache logic |
| `api/semantic_router.py` | Redis semantic router route setup and matching |
| `api/support_service.py` | OpenAI embedding + customer support assistant calls |
| `api/support_faqs.json` | Bundled FAQ knowledge base used for RAG |
| `main.js` | Browser UI and API orchestration |
| `style.css` | Workshop visuals |
| `api/.env` | OpenAI and Redis configuration |

## Runtime architecture

1. Vite serves the front end on port `3000`.
2. FastAPI serves the API on port `8000`.
3. Vite proxies `/api/*` requests to the Python service.
4. The Python service uses:
   - RedisVL and a local Hugging Face vectorizer for semantic cache lookup
   - RedisVL semantic routing for support tool selection
   - OpenAI embeddings for FAQ retrieval
   - OpenAI responses for fresh support answers on cache misses

## Find the starter TODOs

Search for `TODO` in the `code/api` folder. You should find the workshop challenges in:

- `code/api/semantic_cache.py`
- `code/api/semantic_router.py`

The rest of the app is already wired to call these methods. Your job is to complete the Redis cache and router pieces so the UI can show real hits, misses, and route matches.

## Verify the app is healthy

1. Open the `Support Console` panel.
2. Wait for the header badge to show the service check result.
3. You should see:
   - a cache threshold
   - a TTL value
   - the number of cached entries
   - the configured support model

If the page cannot connect, open the `Terminal` panel and check the running logs in tmux.

## Useful terminal commands

Use the terminal or Redis Insight panel to inspect Redis directly:

```bash
redis-cli -u "$REDIS_URL" FT.INFO idx:research_semantic_cache
```

```bash
redis-cli -u "$REDIS_URL" KEYS "semcache:research:*"
```

```bash
redis-cli -u "$REDIS_URL" HGETALL <cache-key>
```

## First checkpoint

Before you start the tasks, confirm these three things:

1. The app loads in the `Support Console` panel.
2. The docs, code editor, terminal, and Redis Insight panels open.
3. The health area is visible. It may report an incomplete cache or router until you finish the TODOs.

Continue to [Task 1](/tasks/task-1.md) once the environment looks healthy.
