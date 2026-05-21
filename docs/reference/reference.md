# Reference

## Architecture summary

- Frontend: Vite app in `code/web`
- API: FastAPI service in `code/api`
- Embeddings: OpenAI embeddings API
- Support answers: OpenAI chat completions through LangChain
- Semantic cache: Redis vector search over cached prompt embeddings
- Semantic router: RedisVL route matching over support tool examples

## Cache fields

Each cached entry stores:

- `question`
- `normalizedQuestion`
- `response`
- `sources`
- `createdAt`
- `createdAtTs`
- `latencyMs`
- `model`
- `embedding`

## Redis commands

Inspect the index:

```bash
redis-cli -u "$REDIS_URL" FT.INFO idx:research_semantic_cache
```

List workshop cache keys:

```bash
redis-cli -u "$REDIS_URL" KEYS "semcache:research:*"
```

Inspect one cached answer:

```bash
redis-cli -u "$REDIS_URL" HGETALL <cache-key>
```

Delete all workshop cache keys manually:

```bash
redis-cli -u "$REDIS_URL" --scan --pattern "semcache:research:*" | xargs redis-cli -u "$REDIS_URL" DEL
```

## API routes

- `GET /api/health`
- `GET /api/cache/stats`
- `POST /api/cache/clear`
- `POST /api/research`
- `POST /api/router/reindex`
- `POST /api/faqs/reindex`

## Suggested experiments

- Change the cache prefix and watch Redis create a new logical namespace
- Lower the TTL and confirm expired entries disappear from the index
- Switch the prompt wording so the answer format changes but the cache behavior remains the same
- Add route examples and compare route distance changes
- Add richer metadata to improve debugging

## Troubleshooting

If requests fail:

1. Check the terminal panel for API errors.
2. Confirm `code/api/.env` still contains valid Redis and OpenAI settings.
3. Verify the local Redis service is running and reachable from the web container.
4. Retry with a fresh cache clear to separate stale data from runtime issues.
