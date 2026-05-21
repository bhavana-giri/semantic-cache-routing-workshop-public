# E-Commerce Support Semantic Cache Workshop

This lab walks you through building a Redis semantic cache and Redis semantic router for an e-commerce customer support assistant. You will fill in the missing RedisVL logic, run the app, and use the UI plus Redis commands to observe each behavior.

## What you will build

- A small customer support assistant that answers live questions
- A Redis semantic cache powered by vector similarity
- A Redis semantic router that chooses the best support tool on cache misses
- A UI that surfaces cache hit or miss state, similarity, matched prompt, and latency
- A UI that surfaces which tool the semantic router selected
- A repeatable workflow for tuning cache thresholds and TTLs

## Why this matters

Traditional caches only help when the new request is identical to a prior request. Customer support workflows are full of paraphrases:

- "My package is running late. Can you check the delivery timeline?"
- "Where is my order? It still hasn't arrived."

Those questions are different strings but nearly the same intent. Semantic caching lets Redis detect that similarity and serve the cached answer when the distance is close enough.

## Workshop flow

1. Read the setup guide and find the TODO comments.
2. Implement the semantic cache creation, check, and store methods.
3. Trigger a cache miss, inspect the newly cached entry, then ask a paraphrase and observe the hit.
4. Implement the semantic router creation and match logic.
5. Exercise FAQ, escalation, blocked, and unknown routing behavior.
6. Tune thresholds and TTLs to see how caching and routing change.

## Where to look

- `Code` panel: edit the frontend and backend
- `Support Console` panel: exercise the workflow
- `Terminal` panel: inspect Redis with `redis-cli`
- `Redis Insight` panel: browse cache keys and index data visually

Start with the [Setup Guide](setup/setup.md), then move to [Task 1](tasks/task-1.md).
