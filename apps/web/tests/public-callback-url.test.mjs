import assert from "node:assert/strict";
import { test } from "node:test";
import { publicCallbackUrl } from "../src/lib/server/public-callback-url.ts";

const internal = "https://0.0.0.0:8080/oauth/google/callback?code=test";
const publicOrigin = "https://decision-radar-web-example.a.run.app";

test("OAuth callback redirects to the configured public host", () => {
  assert.equal(
    publicCallbackUrl("/projects/test/sources?connection=active", internal, publicOrigin, true).href,
    `${publicOrigin}/projects/test/sources?connection=active`,
  );
});

test("production callback fails closed without a public origin", () => {
  assert.throws(() => publicCallbackUrl("/", internal, undefined, true), /RADAR_WEB_ORIGIN/);
  assert.throws(() => publicCallbackUrl("/", internal, "https://0.0.0.0:8080", true), /public web origin/);
});

test("local development keeps the request origin fallback", () => {
  assert.equal(
    publicCallbackUrl("/?connection=failed", "http://localhost:3000/oauth/google/callback", undefined, false).href,
    "http://localhost:3000/?connection=failed",
  );
});
