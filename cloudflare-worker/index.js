/**
 * Cloudflare Worker - License Validation Server
 *
 * Deploy: npx wrangler deploy
 *
 * Keys are stored in the KEYS object below.
 * To add/remove keys, edit this file and redeploy.
 *
 * Format:
 *   "KEY-STRING": { "expires": "YYYY-MM-DD" }
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
  if (env.LICENSE_KEYS) {
    try {
      return JSON.parse(env.LICENSE_KEYS);
    } catch (e) {
      console.error("Failed to parse LICENSE_KEYS env:", e);
    }
  }

  // Fallback to hardcoded keys for backward compatibility
  return {
    "I79M2Q-0U8VTN-MPCUBI": { expires: "2026-05-31" },
    "NEWKEY1-A1B2C3-D4E5F6": { expires: "2026-06-10" },
  };
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
