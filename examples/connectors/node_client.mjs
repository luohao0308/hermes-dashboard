/**
 * Connector SDK example — Node.js client for AI Workflow Control Plane.
 *
 * Demonstrates:
 *   - HMAC-SHA256 webhook signature generation
 *   - Timestamp-based anti-replay
 *   - Batch event ingestion
 *   - Retry with exponential backoff
 *   - event_id idempotency
 *   - Error handling
 *
 * Usage:
 *   export CONNECTOR_URL="http://localhost:8000/api/connectors/YOUR_ID/events"
 *   export WEBHOOK_SECRET="your-webhook-secret"
 *   export SERVICE_TOKEN="your-service-token"
 *   node node_client.mjs
 */

import { createHmac, randomUUID } from 'node:crypto';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const CONNECTOR_URL =
  process.env.CONNECTOR_URL ??
  'http://localhost:8000/api/connectors/00000000-0000-0000-0000-000000000000/events';
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET ?? '';
const SERVICE_TOKEN = process.env.SERVICE_TOKEN ?? '';

const MAX_RETRIES = 3;
const BACKOFF_BASE_MS = 1000;

// ---------------------------------------------------------------------------
// HMAC-SHA256 signature
// ---------------------------------------------------------------------------

/**
 * Generate HMAC-SHA256 signature for a payload.
 *
 * @param {Buffer} payloadBytes - Raw request body.
 * @param {string} secret - Shared webhook secret.
 * @returns {string} Signature in 'sha256=<hex>' format.
 */
function signPayload(payloadBytes, secret) {
  const digest = createHmac('sha256', secret).update(payloadBytes).digest('hex');
  return `sha256=${digest}`;
}

// ---------------------------------------------------------------------------
// Event builder
// ---------------------------------------------------------------------------

/**
 * Build a single connector event with anti-replay timestamp.
 *
 * @param {string} eventType - One of the supported ConnectorEventType values.
 * @param {object} payload - Event-type-specific data.
 * @param {object} [opts] - Optional run_id and event_id.
 * @returns {object} Event object ready for JSON serialization.
 */
function makeEvent(eventType, payload, { runId = null, eventId = null } = {}) {
  return {
    event_type: eventType,
    event_id: eventId ?? randomUUID(),
    run_id: runId,
    timestamp: new Date().toISOString(),
    payload,
  };
}

// ---------------------------------------------------------------------------
// HTTP sender with retry
// ---------------------------------------------------------------------------

/**
 * Send a batch of events to the connector ingestion endpoint.
 *
 * Implements exponential backoff retry on transient failures (429, 5xx).
 *
 * @param {object[]} events - Array of event objects from makeEvent().
 * @param {object} [opts] - Override connectorUrl, webhookSecret, serviceToken.
 * @returns {Promise<object>} Parsed JSON response.
 */
async function sendEvents(events, opts = {}) {
  const url = opts.connectorUrl ?? CONNECTOR_URL;
  const secret = opts.webhookSecret ?? WEBHOOK_SECRET;
  const token = opts.serviceToken ?? SERVICE_TOKEN;

  const bodyBytes = Buffer.from(JSON.stringify(events));

  /** @type {Record<string, string>} */
  const headers = {
    'Content-Type': 'application/json',
  };

  // Auth: prefer service token, fall back to webhook signature
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  } else if (secret) {
    headers['X-Webhook-Signature'] = signPayload(bodyBytes, secret);
  }

  let lastError;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers,
        body: bodyBytes,
        signal: AbortSignal.timeout(30_000),
      });

      if (!resp.ok) {
        const status = resp.status;
        // Retry on 429 (rate limit) and 5xx (server error)
        if ((status === 429 || status >= 500) && attempt < MAX_RETRIES) {
          lastError = new Error(`HTTP ${status}`);
          const delay = BACKOFF_BASE_MS * 2 ** attempt;
          await new Promise((r) => setTimeout(r, delay));
          continue;
        }
        const text = await resp.text();
        throw new Error(`HTTP ${status}: ${text}`);
      }

      return await resp.json();
    } catch (err) {
      lastError = err;
      if (attempt < MAX_RETRIES && (err.name === 'AbortError' || err.code === 'ECONNREFUSED')) {
        const delay = BACKOFF_BASE_MS * 2 ** attempt;
        await new Promise((r) => setTimeout(r, delay));
        continue;
      }
      throw err;
    }
  }

  throw new Error(`All ${MAX_RETRIES} retries exhausted`, { cause: lastError });
}

// ---------------------------------------------------------------------------
// Example usage
// ---------------------------------------------------------------------------

async function main() {
  const runId = randomUUID();

  // Build a batch of events
  const events = [
    // 1. Create a run
    makeEvent('run.created', {
      title: 'Example connector run',
      status: 'running',
      input_summary: 'Processing 3 items',
    }, { runId }),

    // 2. Record a span
    makeEvent('span.created', {
      span_type: 'llm',
      title: 'GPT-4 completion',
      status: 'completed',
      model_name: 'gpt-4',
      input_tokens: 500,
      output_tokens: 200,
      cost: 0.003,
    }, { runId }),

    // 3. Record a tool call
    makeEvent('tool_call.created', {
      tool_name: 'search_docs',
      risk_level: 'read',
      decision: 'allow',
      status: 'completed',
      input_json: { query: 'connector SDK' },
      output_json: { results: 5 },
    }, { runId }),

    // 4. Complete the run
    makeEvent('run.updated', {
      status: 'completed',
      output_summary: 'Processed all items successfully',
      total_tokens: 700,
      total_cost: 0.003,
    }, { runId }),
  ];

  console.log(`Sending ${events.length} events to ${CONNECTOR_URL}`);
  const result = await sendEvents(events);
  console.log(JSON.stringify(result, null, 2));

  // Demonstrate idempotency: send the same events again
  console.log('\nRe-sending same events (should be deduplicated)...');
  const result2 = await sendEvents(events);
  console.log(JSON.stringify(result2, null, 2));
}

main().catch((err) => {
  console.error('Fatal:', err.message);
  process.exit(1);
});
