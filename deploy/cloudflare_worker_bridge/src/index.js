const DEFAULT_LIMIT = 100;
const MAX_LIMIT = 500;
const EVENT_PREFIX = "event:";
const META_SEQUENCE_KEY = "meta:sequence";

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

function eventKey(sequence) {
  return `${EVENT_PREFIX}${String(sequence).padStart(12, "0")}`;
}

function routeParts(url) {
  return url.pathname.split("/").filter(Boolean);
}

function bridgeError(message, status = 400) {
  return jsonResponse(
    {
      status: "error",
      message,
      information_only: true,
      advice: "Nur Fakten-Inbox, keine Anlageberatung und keine Orderausfuehrung.",
    },
    status,
  );
}

function validateEnvironment(env) {
  if (!env.EVENTS) {
    return "KV binding EVENTS fehlt.";
  }
  if (!env.TRADINGVIEW_WEBHOOK_TOKEN) {
    return "Secret TRADINGVIEW_WEBHOOK_TOKEN fehlt.";
  }
  return "";
}

function validateToken(parts, env) {
  return parts.length === 3 && parts[0] === "tv" && parts[1] === env.TRADINGVIEW_WEBHOOK_TOKEN;
}

async function readJsonBody(request) {
  const text = await request.text();
  if (!text.trim()) {
    throw new Error("JSON body fehlt.");
  }
  if (text.length > 65536) {
    throw new Error("JSON body ist zu gross.");
  }
  const payload = JSON.parse(text);
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("JSON body muss ein Objekt sein.");
  }
  return payload;
}

async function nextSequence(env) {
  const currentRaw = await env.EVENTS.get(META_SEQUENCE_KEY);
  const current = Number.parseInt(currentRaw || "0", 10);
  const next = Number.isFinite(current) && current > 0 ? current + 1 : 1;
  await env.EVENTS.put(META_SEQUENCE_KEY, String(next));
  return next;
}

async function storeEvent(env, kind, payload) {
  const sequence = await nextSequence(env);
  const record = {
    sequence,
    kind,
    received_at: new Date().toISOString(),
    payload,
    source: "cloudflare_worker_bridge",
    information_only: true,
  };
  await env.EVENTS.put(eventKey(sequence), JSON.stringify(record), {
    metadata: {
      sequence,
      kind,
      received_at: record.received_at,
    },
  });
  return record;
}

async function listEvents(env, url) {
  const since = Math.max(0, Number.parseInt(url.searchParams.get("since") || "0", 10) || 0);
  const limit = Math.min(
    MAX_LIMIT,
    Math.max(1, Number.parseInt(url.searchParams.get("limit") || String(DEFAULT_LIMIT), 10) || DEFAULT_LIMIT),
  );
  const events = [];
  let cursor;
  do {
    const listed = await env.EVENTS.list({ prefix: EVENT_PREFIX, cursor });
    const pageKeys = listed.keys
      .filter((item) => {
        const sequence = Number.parseInt(String(item.name).slice(EVENT_PREFIX.length), 10);
        return Number.isFinite(sequence) && sequence > since;
      })
      .sort((a, b) => String(a.name).localeCompare(String(b.name)));

    for (const key of pageKeys) {
      const raw = await env.EVENTS.get(key.name);
      if (!raw) {
        continue;
      }
      const record = JSON.parse(raw);
      if (record && typeof record === "object") {
        events.push(record);
      }
      if (events.length >= limit) {
        break;
      }
    }
    cursor = listed.cursor;
    if (listed.list_complete || events.length >= limit) {
      break;
    }
  } while (cursor);
  const lastSequence = events.reduce((max, event) => Math.max(max, Number(event.sequence) || 0), since);
  return jsonResponse({
    status: "ok",
    events,
    count: events.length,
    last_sequence: lastSequence,
    source: "cloudflare_worker_bridge",
    information_only: true,
    disclaimer: "Cloudflare Worker Bridge Pull, keine Anlageberatung und keine Orderausfuehrung.",
  });
}

async function handlePost(request, env, kind) {
  if (!["price", "trade"].includes(kind)) {
    return bridgeError("Route muss /tv/<token>/price oder /tv/<token>/trade sein.", 404);
  }
  let payload;
  try {
    payload = await readJsonBody(request);
  } catch (error) {
    return bridgeError(error.message);
  }
  const record = await storeEvent(env, kind, payload);
  return jsonResponse(
    {
      status: "stored",
      sequence: record.sequence,
      kind: record.kind,
      received_at: record.received_at,
      source: record.source,
      information_only: true,
      disclaimer: "Fakten gespeichert, keine Anlageberatung und keine Orderausfuehrung.",
    },
    202,
  );
}

export default {
  async fetch(request, env) {
    const envError = validateEnvironment(env);
    if (envError) {
      return bridgeError(envError, 500);
    }

    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return jsonResponse({
        status: "ok",
        bridge: "cloudflare_worker_bridge",
        routes: ["/tv/<token>/price", "/tv/<token>/trade", "/tv/<token>/events"],
        information_only: true,
        disclaimer: "Readiness-Check, keine Anlageberatung und keine Orderausfuehrung.",
      });
    }

    const parts = routeParts(url);
    if (!validateToken(parts, env)) {
      return bridgeError("Nicht gefunden.", 404);
    }

    const kind = parts[2];
    if (request.method === "GET" && kind === "events") {
      return listEvents(env, url);
    }
    if (request.method === "POST") {
      return handlePost(request, env, kind);
    }
    return bridgeError("Methode nicht erlaubt.", 405);
  },
};
