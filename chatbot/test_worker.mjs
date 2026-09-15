// test_worker.mjs
// -----------------
// Exercises worker.js's fetch handler directly in Node (which has the same
// Request/Response/fetch primitives Cloudflare Workers use), with global
// fetch mocked so this never calls the real Anthropic API. This is how the
// worker's logic was verified without an actual Cloudflare deployment,
// which this environment has no way to reach.
//
// Run: node chatbot/test_worker.mjs

import worker from "./worker.js";

let pass = 0, fail = 0;
function assert(cond, msg) {
  if (cond) { pass++; }
  else { fail++; console.error("FAIL:", msg); }
}

const realFetch = global.fetch;
function mockAnthropicFetch(responseText, status = 200) {
  global.fetch = async (url, opts) => {
    if (url === "https://api.anthropic.com/v1/messages") {
      return new Response(JSON.stringify({ content: [{ type: "text", text: responseText }] }), { status });
    }
    return realFetch(url, opts);
  };
}

const env = {
  ANTHROPIC_API_KEY: "test-key",
  ALLOWED_ORIGIN: "https://likhitha281.github.io",
  RATE_LIMIT_KV: undefined, // exercise the "KV not configured" path
};

async function run() {
  // 1. OPTIONS preflight returns 204 with CORS headers
  {
    const req = new Request("https://worker.example/chat", {
      method: "OPTIONS",
      headers: { Origin: "https://likhitha281.github.io" },
    });
    const res = await worker.fetch(req, env);
    assert(res.status === 204, "OPTIONS should return 204");
    assert(res.headers.get("Access-Control-Allow-Origin") === "https://likhitha281.github.io", "CORS origin should be echoed for allowed origin");
  }

  // 2. Disallowed origin does not get CORS header back
  {
    const req = new Request("https://worker.example/chat", {
      method: "OPTIONS",
      headers: { Origin: "https://evil.example" },
    });
    const res = await worker.fetch(req, env);
    assert(res.headers.get("Access-Control-Allow-Origin") === null, "CORS origin should NOT be set for a disallowed origin");
  }

  // 3. GET is rejected
  {
    const req = new Request("https://worker.example/chat", { method: "GET" });
    const res = await worker.fetch(req, env);
    assert(res.status === 405, "GET should be rejected with 405");
  }

  // 4. Missing question field -> 400
  {
    const req = new Request("https://worker.example/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dashboardData: {} }),
    });
    const res = await worker.fetch(req, env);
    assert(res.status === 400, "Missing question should 400");
  }

  // 5. Oversized question -> 400
  {
    const req = new Request("https://worker.example/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: "x".repeat(600), dashboardData: {} }),
    });
    const res = await worker.fetch(req, env);
    assert(res.status === 400, "Oversized question should 400");
  }

  // 6. Happy path: valid question -> 200 with the mocked answer text
  {
    mockAnthropicFetch("There are 3 conjunctions tracked, 1 of them HIGH priority.");
    const req = new Request("https://worker.example/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: "How many high priority events are there?",
        dashboardData: { conjunctions_flagged: 3, events: [{ priority_tier: "HIGH" }] },
      }),
    });
    const res = await worker.fetch(req, env);
    const json = await res.json();
    assert(res.status === 200, "Valid request should return 200");
    assert(json.answer.includes("3 conjunctions"), "Answer should pass through the model's text");
  }

  // 7. Missing API key -> 500, and this must be checked BEFORE calling fetch
  {
    const req = new Request("https://worker.example/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: "test", dashboardData: {} }),
    });
    const res = await worker.fetch(req, { ...env, ANTHROPIC_API_KEY: undefined });
    assert(res.status === 500, "Missing API key should 500, not silently proceed");
  }

  // 8. Upstream Anthropic error propagates as 502, not a raw crash
  {
    mockAnthropicFetch("irrelevant", 500);
    const req = new Request("https://worker.example/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: "test", dashboardData: {} }),
    });
    const res = await worker.fetch(req, env);
    assert(res.status === 502, "Upstream 500 should surface as a clean 502, not crash");
  }

  // 9. Rate limiting: in-memory fake KV, limit of 20/hour enforced
  {
    const store = new Map();
    const fakeKV = {
      get: async (k) => store.get(k) ?? null,
      put: async (k, v) => { store.set(k, v); },
    };
    mockAnthropicFetch("ok");
    const rlEnv = { ...env, RATE_LIMIT_KV: fakeKV };
    let lastStatus;
    for (let i = 0; i < 21; i++) {
      const req = new Request("https://worker.example/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", "CF-Connecting-IP": "1.2.3.4" },
        body: JSON.stringify({ question: `q${i}`, dashboardData: {} }),
      });
      const res = await worker.fetch(req, rlEnv);
      lastStatus = res.status;
    }
    assert(lastStatus === 429, "21st request within the hour from the same IP should be rate-limited");
  }

  global.fetch = realFetch;
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail > 0 ? 1 : 0);
}

run();
