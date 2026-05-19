/**
 * Cloudflare Worker - License Validation Server
 *
 * Deploy: npx wrangler deploy
 *
 * License keys are loaded from Cloudflare Secrets/Environment Bindings.
 * Set the LICENSE_KEYS secret with JSON format:
 *   {"KEY-STRING": {"expires": "YYYY-MM-DD"}}
 *
 * For local development, copy .dev.vars.example to .dev.vars
 * and add your test keys there.
 *
 * DO NOT hardcode keys in this file - use environment variables.
 */

// In-memory rate limiting: IP -> { count, resetTime }
const rateLimitStore = new Map();

const RATE_LIMIT_MAX = 10;
const RATE_LIMIT_WINDOW_MS = 5 * 60 * 1000; // 5 minutes
const RATE_LIMIT_RESET_MS = 10 * 60 * 1000; // 10 minutes

function getClientIP(request) {
  return request.headers.get("CF-Connecting-IP") || "unknown";
}

function checkRateLimit(ip) {
  const now = Date.now();
  const record = rateLimitStore.get(ip);

  if (!record) {
    rateLimitStore.set(ip, { count: 1, resetTime: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }

  if (now > record.resetTime) {
    rateLimitStore.set(ip, { count: 1, resetTime: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }

  if (record.count >= RATE_LIMIT_MAX) {
    return false;
  }

  record.count++;
  return true;
}

function getKeys(env) {
  if (!env.LICENSE_KEYS) {
    console.error("LICENSE_KEYS environment variable is not set. Deploy with wrangler secret put LICENSE_KEYS");
    return {};
  }

  try {
    const parsed = JSON.parse(env.LICENSE_KEYS);
    if (typeof parsed !== "object" || parsed === null) {
      console.error("LICENSE_KEYS must be a JSON object");
      return {};
    }
    return parsed;
  } catch (e) {
    console.error("Failed to parse LICENSE_KEYS env:", e);
    return {};
  }
}

export default {
  async fetch(request, env, ctx) {
    // Only allow POST and OPTIONS requests
    if (request.method !== "POST" && request.method !== "OPTIONS") {
      return new Response("Method not allowed", { status: 405 });
    }

    // Handle preflight - return no CORS headers (desktop app has no web origin)
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204 });
    }

    // Rate limiting check
    const clientIP = getClientIP(request);
    if (!checkRateLimit(clientIP)) {
      return new Response(
        JSON.stringify({ valid: false, reason: "rate_limit_exceeded" }),
        {
          status: 429,
          headers: { "Content-Type": "application/json", "Retry-After": "600" },
        },
      );
    }

    try {
      const body = await request.json();
      const key = body.key;

      if (!key) {
        return new Response(
          JSON.stringify({ valid: false, reason: "invalid" }),
          { headers: { "Content-Type": "application/json" } },
        );
      }

      const KEYS = getKeys(env);

      if (Object.keys(KEYS).length === 0) {
        return new Response(
          JSON.stringify({ valid: false, reason: "server_not_configured" }),
          { status: 503, headers: { "Content-Type": "application/json" } },
        );
      }

      const keyData = KEYS[key];

      if (!keyData) {
        return new Response(
          JSON.stringify({ valid: false, reason: "invalid" }),
          { headers: { "Content-Type": "application/json" } },
        );
      }

      // Check expiration
      const expires = new Date(keyData.expires);
      const now = new Date();

      if (now > expires) {
        return new Response(
          JSON.stringify({ valid: false, reason: "expired" }),
          { headers: { "Content-Type": "application/json" } },
        );
      }

      return new Response(JSON.stringify({ valid: true }), {
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return new Response(JSON.stringify({ valid: false, reason: "invalid" }), {
        headers: { "Content-Type": "application/json" },
      });
    }
  },
};
