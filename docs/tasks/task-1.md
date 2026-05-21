# Task 1: Build the Semantic Cache

## Goal

Fill in the RedisVL semantic cache implementation in `code/api/semantic_cache.py`.

By the end of this task, the API can:

- create a RedisVL `SemanticCache`
- check for a nearby cached prompt
- return a hit when the vector distance is within threshold
- store a new answer after a miss

## Step 1: Create the cache

Open `code/api/semantic_cache.py`.

Find the TODO in `ensure_cache`.

Create a `SemanticCache` with:

- `name=self.settings.cache_index_name`
- `redis_client=self.client`
- `vectorizer=HFTextVectorizer(model=self.settings.cache_embedding_model)`
- `distance_threshold=self.settings.cache_distance_threshold`
- `ttl=self.settings.cache_ttl_seconds`
- `overwrite=True`

## Step 2: Check the cache

Find the TODO in `check`.

Call the cache with the incoming question and ask for the nearest result:

- `prompt=question`
- `num_results=1`

The code below the TODO already handles the miss and hit response shape.

## Step 3: Store a response

Find the TODO in `store`.

Store the fresh support answer with:

- `prompt=question`
- `response=response`
- the existing metadata dictionary
- `ttl=self.settings.cache_ttl_seconds`

## Step 4: Restart and verify syntax

Save the file. The API should reload automatically in the workbench.

If it does not, use the terminal panel to restart the stack:

```bash
docker compose up --build
```

## Checkpoint

Open the `Support Console` panel and confirm the health badge can connect.

Next: [Task 2: Observe a Miss, Then a Hit](/tasks/task-2.md)
