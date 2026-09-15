# Dashboard chatbot — backend

A Cloudflare Worker that lets the static dashboard (`docs/index.html`) offer
a natural-language Q&A chatbot without exposing your Anthropic API key in
client-side JavaScript. See the docstring at the top of `worker.js` for why
this needs a backend at all — short version: GitHub Pages is static
hosting, and an API key can never safely live in code the browser can read.

## What it does, and doesn't do

- Answers questions grounded in the dashboard's *current* JSON snapshot
  (`docs/latest.json`), sent from the browser with each request.
- Explicitly instructed not to invent numbers not present in that data —
  same "never alter the numbers" philosophy as `src/analyst.py` in the main
  pipeline. This is a Q&A layer over known data, not an autonomous agent.
- Does **not** have access to the full SQLite observation history — only
  whatever's in the current dashboard snapshot. Ask it about a historical
  trend beyond that and it should say so rather than guess.

## Deploy it (one-time, ~10 minutes)

1. **Create a free Cloudflare account** at cloudflare.com if you don't
   have one.
2. **Install Wrangler** (Cloudflare's CLI): `npm install -g wrangler`
3. **Log in**: `wrangler login` (opens a browser to authenticate)
4. **From this `chatbot/` folder**, set your API key as a secret (never
   goes into a file, stored encrypted by Cloudflare):
   ```bash
   wrangler secret put ANTHROPIC_API_KEY
   ```
   Paste your key when prompted.
5. **Deploy**: `wrangler deploy`. Wrangler prints a URL like
   `https://orbital-risk-chatbot.YOUR-SUBDOMAIN.workers.dev` — that's your
   chatbot backend.
6. **Wire it into the dashboard**: open `docs/index.html`, find
   `CHATBOT_WORKER_URL`, and replace the placeholder with the URL from
   step 5. Commit and push.

### Optional: rate limiting

Without this step, rate limiting is silently skipped (see `worker.js`) —
the chatbot still works, just without the per-IP hourly cap.

```bash
wrangler kv namespace create RATE_LIMIT_KV
```
Copy the `id` it prints into the commented-out `[[kv_namespaces]]` block in
`wrangler.toml`, uncomment it, then `wrangler deploy` again.

## Honest security notes — read before making this public

- **CORS restricts which *websites* can call this from a browser, not who
  can call it at all.** Anyone can still `curl` your Worker URL directly,
  bypassing CORS entirely — CORS is a browser-enforced convention, not a
  server-side authorization mechanism. The rate limiter (if enabled) is
  the actual abuse control, not CORS.
- **Set a spending limit on your Anthropic API key.** This is a public
  endpoint by design (that's the point — visitors to your dashboard can
  use it without logging in). A spending cap is the real backstop against
  a bad actor hammering it directly, not the app-layer protections above.
- **`MAX_TOKENS = 300`** in `worker.js` bounds cost per request. Raise it
  only if you also add a real usage cap, not just a UI text limit.

## Testing

```bash
node test_worker.mjs
```

Runs the worker's request-handling logic directly in Node (which shares
Cloudflare Workers' Request/Response/fetch primitives) with the Anthropic
call mocked — verifies CORS behavior, input validation, rate limiting, and
error handling without needing a live deployment or a real API key.
