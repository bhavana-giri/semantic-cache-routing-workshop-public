const samplePrompts = [
  'How do I place an order?',
  'How long does delivery take?',
  'What is your return policy?',
  'I forgot my password. What should I do?'
];

const promptBank = document.getElementById('prompt-bank');
const form = document.getElementById('research-form');
const questionInput = document.getElementById('research-question');
const submitButton = document.getElementById('submit-button');
const clearCacheButton = document.getElementById('clear-cache-button');
const requestStatus = document.getElementById('request-status');
const cacheHitPill = document.getElementById('cache-hit-pill');
const cacheMessage = document.getElementById('cache-message');
const matchedQuestion = document.getElementById('matched-question');
const similarityScore = document.getElementById('similarity-score');
const distanceScore = document.getElementById('distance-score');
const latencyScore = document.getElementById('latency-score');
const servedBy = document.getElementById('served-by');
const answerOutput = document.getElementById('answer-output');
const sourceList = document.getElementById('source-list');
const cacheThreshold = document.getElementById('cache-threshold');
const cacheTtl = document.getElementById('cache-ttl');
const cacheSize = document.getElementById('cache-size');
const routerThreshold = document.getElementById('router-threshold');
const healthStatus = document.getElementById('health-status');
const selectedTool = document.getElementById('selected-tool');
const selectedModel = document.getElementById('selected-model');

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderMarkdown(markdown) {
  const sanitized = escapeHtml(markdown.trim());
  const withHeadings = sanitized
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h1>$1</h1>');

  const sections = withHeadings
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      if (block.startsWith('<h1>') || block.startsWith('<h2>') || block.startsWith('<h3>')) {
        return block;
      }

      if (block.split('\n').every((line) => line.startsWith('- ') || line.startsWith('* '))) {
        const items = block
          .split('\n')
          .map((line) => line.replace(/^[-*]\s+/, '').trim())
          .map((line) => `<li>${line}</li>`)
          .join('');

        return `<ul>${items}</ul>`;
      }

      return `<p>${block.replace(/\n/g, '<br>')}</p>`;
    });

  return sections.join('');
}

function formatNumber(value, digits = 2) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '-';
}

function setBusyState(isBusy) {
  submitButton.disabled = isBusy;
  clearCacheButton.disabled = isBusy;
}

function renderSources(sources) {
  if (!sources || sources.length === 0) {
    sourceList.innerHTML = '<li class="placeholder">No FAQ references matched this request.</li>';
    return;
  }

  sourceList.innerHTML = sources
    .map((source) => {
      const title = escapeHtml(source.title || 'Support FAQ');
      const content = source.content ? `<p>${escapeHtml(source.content)}</p>` : '';

      if (source.url) {
        const href = escapeHtml(source.url);
        return `<li><a href="${href}" target="_blank" rel="noreferrer">${title}</a>${content}</li>`;
      }

      return `<li><strong>${title}</strong>${content}</li>`;
    })
    .join('');
}

function renderResponse(data) {
  const isHit = data.cache.hit;
  const toolName = data.routing?.toolName || 'unknown';
  const routeMode = data.routing?.mode || 'unknown';
  const modelName = data.routing?.modelName || data.metadata?.model || 'Unknown model';
  cacheHitPill.className = `state-pill ${isHit ? 'hit' : 'miss'}`;
  cacheHitPill.textContent = isHit ? 'Cache hit' : 'Cache miss';
  cacheMessage.textContent = isHit
    ? `Redis returned a semantically similar support answer. Semantic routing would have used the ${toolName} route.`
    : `Redis routed this request to the ${toolName} route (${routeMode}), produced a fresh response, and cached it.`;
  selectedTool.textContent = toolName;
  selectedModel.textContent = modelName;
  matchedQuestion.textContent = data.cache.matchedQuestion || 'No prior semantic match';
  similarityScore.textContent = formatNumber(data.cache.similarity);
  distanceScore.textContent = formatNumber(data.cache.distance);
  latencyScore.textContent = `${Math.round(data.metadata.latencyMs)} ms`;
  servedBy.textContent = `${data.metadata.servedBy} · ${data.metadata.model}`;
  answerOutput.innerHTML = renderMarkdown(data.answer);
  renderSources(data.sources);
}

function renderCacheStats(data) {
  cacheThreshold.textContent = formatNumber(data.policy?.cacheDistanceThreshold);
  cacheTtl.textContent = `${Math.round(data.policy?.cacheTtlSeconds ?? 0)}`;
  cacheSize.textContent = `${data.cache.numEntries}`;
  routerThreshold.textContent = formatNumber(data.policy?.routerDistanceThreshold);
  healthStatus.textContent = data.ok
    ? 'Connected to Redis and ready.'
    : `Service check failed: ${data.error || 'Redis is unreachable.'}`;
}

async function refreshHealth() {
  const response = await fetch('/api/health');
  const data = await response.json();
  renderCacheStats(data);
  if (!response.ok) {
    throw new Error(data.error || 'Health check failed.');
  }
}

async function handleSubmit(event) {
  event.preventDefault();
  const question = questionInput.value.trim();

  if (!question) {
    requestStatus.textContent = 'Add a customer question first.';
    questionInput.focus();
    return;
  }

  setBusyState(true);
  requestStatus.textContent = 'Running embeddings, semantic cache lookup, router lookup, FAQ retrieval, and support flow…';

  try {
    const response = await fetch('/api/research', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ question })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Request failed.');
    }

    renderResponse(data);
    requestStatus.textContent = data.cache.hit
      ? `Semantic cache served the support answer. Router match: ${data.routing?.toolName || 'unknown'}.`
      : `Router selected ${data.routing?.toolName || 'unknown'}. Fresh answer generated and added to the cache.`;
    await refreshHealth();
  } catch (error) {
    requestStatus.textContent = String(error.message || error);
    answerOutput.innerHTML = `<p class="placeholder">${escapeHtml(String(error.message || error))}</p>`;
  } finally {
    setBusyState(false);
  }
}

async function handleClearCache() {
  setBusyState(true);
  requestStatus.textContent = 'Clearing Redis semantic cache…';

  try {
    const response = await fetch('/api/cache/clear', { method: 'POST' });
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || 'Unable to clear cache.');
    }

    await refreshHealth();
    requestStatus.textContent = 'Cache cleared. The next question will be a fresh miss.';
    cacheHitPill.className = 'state-pill neutral';
    cacheHitPill.textContent = 'Reset';
    cacheMessage.textContent = 'The semantic cache is empty again.';
    matchedQuestion.textContent = '-';
    selectedTool.textContent = '-';
    selectedModel.textContent = '-';
    similarityScore.textContent = '-';
    distanceScore.textContent = '-';
    latencyScore.textContent = '-';
    servedBy.textContent = 'Not run yet';
    answerOutput.innerHTML = '<p class="placeholder">The customer support reply will appear here.</p>';
    sourceList.innerHTML = '<li class="placeholder">FAQ references will appear when the assistant uses them.</li>';
  } catch (error) {
    requestStatus.textContent = String(error.message || error);
  } finally {
    setBusyState(false);
  }
}

function renderPromptBank(prompts) {
  promptBank.innerHTML = prompts
    .map((prompt) => `<button class="chip-button" type="button">${escapeHtml(prompt)}</button>`)
    .join('');

  for (const button of promptBank.querySelectorAll('button')) {
    button.addEventListener('click', () => {
      questionInput.value = button.textContent;
      questionInput.focus();
    });
  }
}

form.addEventListener('submit', handleSubmit);
clearCacheButton.addEventListener('click', handleClearCache);

renderPromptBank(samplePrompts);
refreshHealth().catch((error) => {
  healthStatus.textContent = `Health check failed: ${String(error.message || error)}`;
});
