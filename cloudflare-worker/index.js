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

const KEYS = {
  "I79M2Q-0U8VTN-MPCUBI": { expires: "2026-05-23" },
};

export default {
  async fetch(request, env, ctx) {
    // Only allow POST requests
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    // CORS headers
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    // Handle preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      const body = await request.json();
      const key = body.key;

      if (!key) {
        return new Response(
          JSON.stringify({ valid: false, reason: "invalid" }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" } },
        );
      }

      const keyData = KEYS[key];

      if (!keyData) {
        return new Response(
          JSON.stringify({ valid: false, reason: "invalid" }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" } },
        );
      }

      // Check expiration
      const expires = new Date(keyData.expires);
      const now = new Date();

      if (now > expires) {
        return new Response(
          JSON.stringify({ valid: false, reason: "expired" }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" } },
        );
      }

      return new Response(JSON.stringify({ valid: true }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    } catch (error) {
      return new Response(JSON.stringify({ valid: false, reason: "invalid" }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
  },
};
