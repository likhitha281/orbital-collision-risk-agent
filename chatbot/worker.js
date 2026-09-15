/**
 * worker.js
 * ----------
 * Cloudflare Worker backend for the dashboard's Q&A chatbot.
 *
 * Why this exists as a separate backend at all: the dashboard
 * (docs/index.html) is static — GitHub Pages serves plain HTML/JS with no
 * server. An LLM call needs an API key, and an API key can never live in
 * client-side JavaScript (anyone can open dev tools and read it). This
 * Worker is the minimum viable way to keep the key server-side while still
 * letting a static site use it: the browser calls this Worker, the Worker
 * calls Anthropic, the key never leaves Cloudflare's servers.
 *
 * Grounding, same philosophy as the rest of this project: the model is
 * given the dashboard's current JSON data and instructed to answer only
 * from it, not to invent numbers. This is a Q&A layer over known data, not
 * an autonomous agent — same distinction the main README draws for the
 * rest of the pipeline.
 *
 * Deploy: see chatbot/README.md. Requires `wrangler` and a Cloudflare
 * account (free tier) — this sandbox has no way to actually deploy or
 * hit a live Cloudflare endpoint, so the request/response logic below was
 * verified locally against Node's built-in fetch/Request/Response (see
 * chatbot/test_worker.mjs) rather than against a real deployment.
 */

const ANTHROPIC_MODEL = "claude-sonnet-4-6";
const ANTHROPIC_URL = "https://api.anthropic.com/v1/messages";
const MAX_TOKENS = 300; // keeps cost per request bounded on a public endpoint
const MAX_QUESTION_LENGTH = 500;
const RATE_LIMIT_PER_HOUR = 20; // per IP, via Workers KV — see README for the caveat this doesn't fully prevent abuse

const SYSTEM_PROMPT = `You are a Q&A assistant for a satellite collision-risk dashboard.

You will be given the dashboard's current data as JSON, and a user question.

Rules:
- Answer ONLY using the data provided. Never invent a probability, priority score, object name, or date not present in the data.
- If the question can't be answered from the provided data, say so plainly — don't guess.
- Keep answers short (2-4 sentences) and concrete: cite the actual object names and numbers from the data.
- If asked about historical trends beyond what's in the provided snapshot, say that only the current snapshot is available to you, not full history.
- You are not a decision-maker. Do not recommend specific maneuvers or claim operational certainty.`;

function corsHeaders(origin, allowedOrigin) {
  const headers = {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
  if (origin === allowedOrigin) {
    headers["Access-Control-Allow-Origin"] = allowedOrigin;
  }
  return headers;
}

async function checkRateLimit(env, ip) {
  if (!env.RATE_LIMIT_KV) return true; // KV not configured — skip limiting rather than fail closed on a misconfigured binding
  const key = `rl:${ip}:${new Date().toISOString().slice(0, 13)}`; // per-IP, per-hour bucket
  const current = parseInt((await env.RATE_LIMIT_KV.get(key)) || "0", 10);
  if (current >= RATE_LIMIT_PER_HOUR) return false;
  await env.RATE_LIMIT_KV.put(key, String(current + 1), { expirationTtl: 3600 });
  return true;
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowedOrigin = env.ALLOWED_ORIGIN || "https://likhitha281.github.io";
    const cors = corsHeaders(origin, allowedOrigin);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    if (request.method !== "POST") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { "Content-Type": "application/json", ...cors },
      });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
        status: 400,
        headers: { "Content-Type": "application/json", ...cors },
      });
    }

    const { question, dashboardData } = body || {};
    if (!question || typeof question !== "string") {
      return new Response(JSON.stringify({ error: "Missing 'question' field" }), {
        status: 400,
        headers: { "Content-Type": "application/json", ...cors },
      });
    }
    if (question.length > MAX_QUESTION_LENGTH) {
      return new Response(JSON.stringify({ error: `Question too long (max ${MAX_QUESTION_LENGTH} chars)` }), {
        status: 400,
        headers: { "Content-Type": "application/json", ...cors },
      });
    }

    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    const withinLimit = await checkRateLimit(env, ip);
    if (!withinLimit) {
      return new Response(JSON.stringify({ error: "Rate limit exceeded. Try again later." }), {
        status: 429,
        headers: { "Content-Type": "application/json", ...cors },
      });
    }

    if (!env.ANTHROPIC_API_KEY) {
      return new Response(JSON.stringify({ error: "Server not configured (missing API key)" }), {
        status: 500,
        headers: { "Content-Type": "application/json", ...cors },
      });
    }

    const userContent = `Dashboard data:\n${JSON.stringify(dashboardData || {}, null, 2)}\n\nQuestion: ${question}`;

    let anthropicResponse;
    try {
      anthropicResponse = await fetch(ANTHROPIC_URL, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-api-key": env.ANTHROPIC_API_KEY,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: ANTHROPIC_MODEL,
          max_tokens: MAX_TOKENS,
          system: SYSTEM_PROMPT,
          messages: [{ role: "user", content: userContent }],
        }),
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: "Failed to reach the model API" }), {
        status: 502,
        headers: { "Content-Type": "application/json", ...cors },
      });
    }

    if (!anthropicResponse.ok) {
      return new Response(JSON.stringify({ error: `Model API error (${anthropicResponse.status})` }), {
        status: 502,
        headers: { "Content-Type": "application/json", ...cors },
      });
    }

    const data = await anthropicResponse.json();
    const text = (data.content || [])
      .filter((b) => b.type === "text")
      .map((b) => b.text)
      .join("\n")
      .trim();

    return new Response(JSON.stringify({ answer: text || "(no response)" }), {
      status: 200,
      headers: { "Content-Type": "application/json", ...cors },
    });
  },
};
