# Task 4: Tune and Extend

## Goal

Experiment beyond the default cache and router behavior.

## Option A: Tune the cache threshold

Open `code/api/.env`.

Find:

```text
CACHE_DISTANCE_THRESHOLD=0.12
```

Make the cache stricter:

```text
CACHE_DISTANCE_THRESHOLD=0.08
```

Save the file, wait for the API to reload, clear the cache, and repeat the Task 2 prompts.

Then make the cache looser:

```text
CACHE_DISTANCE_THRESHOLD=0.18
```

Ask a more distant question and watch whether Redis starts reusing answers too aggressively.

## Option B: Tune the router threshold

Open `code/api/.env`.

Find:

```text
ROUTER_DISTANCE_THRESHOLD=0.5
```

Lower values make routes stricter. Higher values make the router more willing to classify distant prompts.

Try:

```text
ROUTER_DISTANCE_THRESHOLD=0.35
```

Then retry the unknown route prompt from Task 3.

## Option C: Change the support instructions

Open `code/api/support_service.py`.

Find the system prompt in `SupportService.__init__` and modify the answer format. For example, ask the model to always include:

- a decision recommendation
- a risk list
- a short executive summary

Save the file and run a fresh miss to see the new output.

## Option D: Add more metadata to the cache

Open `code/api/semantic_cache.py`.

Extend the stored metadata with something useful, such as:

- `topic`
- `audience`
- `requestId`

Then surface the new field in the UI.

## Stretch goal

Add a `top K matches` debug view instead of just the nearest hit. This is useful when you want to compare multiple possible semantic matches before deciding which answer to reuse.

## What you learned

- Thresholds control semantic matching behavior
- Route examples and thresholds shape tool selection
- Cache design is tightly coupled to prompt design and observability

Check the [Reference](/reference/reference.md) section for architecture notes and command snippets.
