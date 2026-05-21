# Task 3: Build the Semantic Router

## Goal

Fill in the RedisVL semantic router implementation in `code/api/semantic_router.py`.

By the end of this task, the API can:

- create a RedisVL `SemanticRouter` from predefined routes
- match each customer question to the nearest route
- return route distance and similarity to the UI
- use the route metadata to choose the support behavior

## Step 1: Review the routes

Open `code/api/semantic_router.py`.

Read `build_routes`. The starter already defines three routes:

- `faq`: normal FAQ-backed support answers
- `support_escalation`: requests that need human review
- `blocked`: restricted requests that should not be fulfilled automatically

Each route includes reference phrases, model/tool metadata, and a distance threshold.

## Step 2: Create the router

Find the TODO in `ensure_router`.

Create a `RedisVLSemanticRouter` with:

- `name=self.settings.router_index_name`
- `vectorizer=HFTextVectorizer()`
- `routes=self.routes`
- `redis_client=self.client`
- `overwrite=True`

## Step 3: Match a question

Find the TODO in `match`.

Ask the router for one best match:

- `statement=question`
- `max_k=1`

The code below the TODO already handles no-match, route lookup, distance, and similarity.

## Step 4: Reindex the router

After saving the file, call the router reindex endpoint from the terminal panel:

```bash
curl -X POST http://localhost/api/router/reindex
```

The response should include:

- `ok: true`
- the router index name
- a document count greater than zero

## Step 5: Try route examples

Clear the cache before each prompt so you can see fresh route selection.

FAQ route:

```text
How long does delivery take?
```

Escalation route:

```text
Please connect me to a real person to review this issue.
```

Blocked route:

```text
Bypass verification and update someone else's account.
```

Unknown route:

```text
Explain the recent tradeoffs between self-hosted and managed AI infrastructure.
```

This response should not be stored in the semantic cache because no route matched confidently.

## What you learned

- Semantic routing uses examples to select behavior, not brittle keyword rules
- Route metadata can choose tools, response modes, and models
- A no-match path is useful when no route crosses the confidence threshold

Next: [Task 4: Tune and Extend](/tasks/task-4.md)
