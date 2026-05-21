# Task 2: Observe a Miss, Then a Hit

## Goal

See the semantic cache behave like the Python reference logic:

- `check` for a nearby prompt
- return a hit when the vector distance is within threshold
- `store` a new answer after a miss

## Step 1: Clear the cache

1. Open the `Support Console` panel.
2. Click `Clear cache`.
3. Confirm the cached entry count resets.

## Step 2: Trigger a cache miss

Use this first question:

```text
How do I place an order?
```

What to look for:

- The UI should show `Cache miss`
- `servedBy` should show `fallback_faq:faq_rag` until you complete Task 3
- Redis entry count should increase by one

## Step 3: Ask a paraphrase

Ask the same intent with different wording. This is the moment where semantic
cache behavior is different from an exact-match cache.

Now ask:

```text
How can I place an order on your website?
```

What to look for:

- The UI should ideally show `Cache hit`
- `matched prompt` should show the original question
- latency should be lower than the first request

## Step 4: Inspect Redis

In the terminal panel, inspect the index and stored keys:

```bash
redis-cli -u "$REDIS_URL" FT.INFO idx:research_semantic_cache
```

```bash
redis-cli -u "$REDIS_URL" KEYS "semcache:research:*"
```

Inspect one cached answer:

```bash
redis-cli -u "$REDIS_URL" HGETALL <cache-key>
```

## What you learned

- Semantic cache lookups use vector similarity, not exact string matches
- Cache misses generate fresh answers and immediately populate Redis
- Paraphrased follow-up questions can reuse the same cached answer

Next: [Task 3: Build the Semantic Router](/tasks/task-3.md)
