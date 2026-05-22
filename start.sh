#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ROOT_DIR}/code/api/.env"

create_env_file() {
  if [ -f "${ENV_FILE}" ]; then
    echo "Using existing code/api/.env"
    return
  fi

  mkdir -p "$(dirname "${ENV_FILE}")"

  if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "WARNING: OPENAI_API_KEY is not set. Creating code/api/.env with a placeholder."
    echo "Set OPENAI_API_KEY as a runtime environment variable before starting the lab."
  fi

  echo "Creating code/api/.env from runtime environment variables."
  cat > "${ENV_FILE}" <<EOF
OPENAI_API_KEY=${OPENAI_API_KEY:-your-openai-api-key}
REDIS_URL=${REDIS_URL:-redis://redis:6379}
PORT=${PORT:-8000}
OPENAI_MODEL=${OPENAI_MODEL:-gpt-4.1-mini}
MODEL_FAST=${MODEL_FAST:-gpt-4.1-mini}
MODEL_BALANCED=${MODEL_BALANCED:-${OPENAI_MODEL:-gpt-4.1-mini}}
MODEL_DEEP=${MODEL_DEEP:-gpt-4.1}
CACHE_EMBEDDING_MODEL=${CACHE_EMBEDDING_MODEL:-redis/langcache-embed-v3-small}
EMBEDDING_MODEL=${EMBEDDING_MODEL:-text-embedding-3-small}
EMBEDDING_DIMENSIONS=${EMBEDDING_DIMENSIONS:-1536}
CACHE_INDEX_NAME=${CACHE_INDEX_NAME:-idx:research_semantic_cache}
CACHE_PREFIX=${CACHE_PREFIX:-semcache:research:}
CACHE_TTL_SECONDS=${CACHE_TTL_SECONDS:-86400}
CACHE_DISTANCE_THRESHOLD=${CACHE_DISTANCE_THRESHOLD:-0.12}
ROUTER_INDEX_NAME=${ROUTER_INDEX_NAME:-idx:support_semantic_router}
ROUTER_PREFIX=${ROUTER_PREFIX:-semrouter:support:}
ROUTER_DISTANCE_THRESHOLD=${ROUTER_DISTANCE_THRESHOLD:-0.3}
FAQ_INDEX_NAME=${FAQ_INDEX_NAME:-idx:faq_semantic_router}
FAQ_PREFIX=${FAQ_PREFIX:-faqrouter:support:}
FAQ_DISTANCE_THRESHOLD=${FAQ_DISTANCE_THRESHOLD:-0.45}
FAQ_SEARCH_LIMIT=${FAQ_SEARCH_LIMIT:-3}
EOF
}

create_env_file
cd "${ROOT_DIR}"
docker compose up -d
