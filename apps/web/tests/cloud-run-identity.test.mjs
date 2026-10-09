import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { cloudRunIdentityHeader } from "../src/lib/server/cloud-run-identity.ts";

const originalFetch = globalThis.fetch;
const originalAudience = process.env.RADAR_API_AUDIENCE;

afterEach(() => {
  globalThis.fetch = originalFetch;
  if (originalAudience === undefined) delete process.env.RADAR_API_AUDIENCE;
  else process.env.RADAR_API_AUDIENCE = originalAudience;
});

test("local API calls do not ask the metadata server for an identity", async () => {
  delete process.env.RADAR_API_AUDIENCE;
  globalThis.fetch = () => { throw new Error("metadata must not be queried"); };
  assert.equal(await cloudRunIdentityHeader(), null);
});

test("private API calls use a metadata token for the configured audience", async () => {
  const audience = "https://decision-radar-api-staging-example.a.run.app";
  process.env.RADAR_API_AUDIENCE = audience;
  globalThis.fetch = async (url, options) => {
    assert.equal(url.hostname, "metadata.google.internal");
    assert.equal(url.searchParams.get("audience"), audience);
    assert.equal(options.headers["Metadata-Flavor"], "Google");
    return new Response("test-identity-token", { status: 200 });
  };
  assert.equal(await cloudRunIdentityHeader(), "Bearer test-identity-token");
});

test("metadata failure stops the private API call", async () => {
  process.env.RADAR_API_AUDIENCE = "https://private-api.example";
  globalThis.fetch = async () => new Response("unavailable", { status: 503 });
  await assert.rejects(cloudRunIdentityHeader(), /Unable to obtain/);
});
