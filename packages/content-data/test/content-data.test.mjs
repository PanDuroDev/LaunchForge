import test from "node:test";
import assert from "node:assert/strict";
import {
  fetchJson, ContentError, mapFields, MappingError, inspectResponse,
} from "../dist/index.js";

const json = (body, status = 200, headers = { "content-type": "application/json" }) =>
  new Response(JSON.stringify(body), { status, headers });

test("fetches HTTPS JSON with bounded GET defaults", async () => {
  let init;
  const result = await fetchJson({ url: "https://publisher.example/content.json" }, async (_url, options) => {
    init = options;
    return json({ news: [{ title: "Launch" }] });
  });
  assert.equal(result.news[0].title, "Launch");
  assert.equal(init.method, "GET");
  assert.equal(init.credentials, "omit");
  assert.equal(init.redirect, "manual");
  assert.equal(init.referrerPolicy, "no-referrer");
});

test("rejects insecure URLs, embedded credentials and secret query parameters", async () => {
  await assert.rejects(fetchJson({ url: "http://publisher.example/data.json" }), e => e.code === "insecure_url");
  await assert.rejects(fetchJson({ url: "https://user:pass@publisher.example/data.json" }), e => e.code === "invalid_url");
  await assert.rejects(fetchJson({ url: "https://publisher.example/data.json?api_key=abc" }), e => e.code === "invalid_url");
  await assert.rejects(fetchJson({ url: "https://publisher.example/data.json", method: "POST" }), e => e.code === "invalid_request");
});

test("rejects cross-origin and excessive redirects", async () => {
  await assert.rejects(fetchJson({ url: "https://a.example/data" }, async () =>
    new Response(null, { status: 302, headers: { location: "https://b.example/other" } })
  ), e => e.code === "redirect_rejected");
  await assert.rejects(fetchJson({ url: "https://a.example/data", limits: { maxRedirects: 0 } }, async () =>
    new Response(null, { status: 302, headers: { location: "/next" } })
  ), e => e.code === "redirect_rejected");
});

test("allows same-origin redirects and strips sensitive request headers", async () => {
  const seen = [];
  const result = await fetchJson({ url: "https://a.example/data", headers: { authorization: "Bearer test-secret", "x-client": "demo" } }, async (url, init) => {
    seen.push({ url: String(url), headers: new Headers(init.headers) });
    return seen.length === 1
      ? new Response(null, { status: 302, headers: { location: "/next" } })
      : json({ ok: true });
  });
  assert.equal(result.ok, true);
  assert.equal(seen[1].headers.has("authorization"), false);
  assert.equal(seen[1].headers.get("x-client"), "demo");
});

test("enforces body byte caps and JSON content type", async () => {
  await assert.rejects(fetchJson({ url: "https://a.example/data", limits: { maxBytes: 4 } }, async () =>
    new Response('{"large":true}', { headers: { "content-type": "application/json" } })
  ), e => e.code === "response_too_large");
  await assert.rejects(fetchJson({ url: "https://a.example/data" }, async () =>
    new Response("{}", { headers: { "content-type": "text/html" } })
  ), e => e.code === "invalid_content_type");
});

test("rejects malformed JSON and prototype-sensitive structures", async () => {
  await assert.rejects(fetchJson({ url: "https://a.example/data" }, async () =>
    new Response("{bad", { headers: { "content-type": "application/json" } })
  ), e => e.code === "invalid_json");
  const polluted = JSON.parse('{"__proto__":{"polluted":true}}');
  await assert.rejects(fetchJson({ url: "https://a.example/data" }, async () =>
    new Response(JSON.stringify(polluted), { headers: { "content-type": "application/json" } })
  ), e => e.code === "invalid_json_structure");
});

test("enforces timeout and caller cancellation while reading response", async () => {
  const hangs = (_url, init) => new Promise((_resolve, reject) => {
    init.signal.addEventListener("abort", () => reject(new Error("aborted")), { once: true });
  });
  await assert.rejects(fetchJson({ url: "https://a.example/data", limits: { timeoutMs: 250, retries: 0 } }, hangs), e => e.code === "timeout");
  const controller = new AbortController();
  const request = fetchJson({ url: "https://a.example/data", signal: controller.signal, limits: { retries: 0 } }, hangs);
  controller.abort();
  await assert.rejects(request, e => e.code === "cancelled");
});

test("retries transient HTTP errors only within configured bound", async () => {
  let calls = 0;
  const result = await fetchJson({ url: "https://a.example/data", limits: { retries: 1, retryBaseDelayMs: 0 } }, async () => {
    calls++;
    return calls === 1 ? new Response("busy", { status: 503 }) : json({ ok: true });
  });
  assert.equal(calls, 2);
  assert.equal(result.ok, true);
});

test("maps RFC6901 fields with defaults, optional values and safe transforms", () => {
  const mapped = mapFields({ item: { "display/name": "  Demo  ", count: "12" } }, [
    { field: "title", source: "/item/display~1name", type: "string", transforms: ["trim"] },
    { field: "count", source: "/item/count", type: "number", transforms: ["toNumber"] },
    { field: "missing", source: "/item/optional", type: "string", optional: true },
    { field: "fallback", source: "/missing", type: "boolean", defaultValue: false }
  ]);
  assert.equal(mapped.title, "Demo");
  assert.equal(mapped.count, 12);
  assert.equal(Object.hasOwn(mapped, "missing"), false);
  assert.equal(mapped.fallback, false);
});

test("rejects invalid, ambiguous and prototype-sensitive mappings", () => {
  assert.throws(() => mapFields({ a: 1 }, [{ field: "name", source: "/missing", type: "string" }]), MappingError);
  assert.throws(() => mapFields({ a: 1 }, [{ field: "name", source: "/a", type: "string" }]), e => e.code === "type_mismatch");
  assert.throws(() => mapFields({}, [{ field: "__proto__", source: "", type: "any" }]), MappingError);
  assert.throws(() => mapFields({ a: 1 }, [{ field: "a", source: "/a", type: "number", transforms: ["eval"] }]), MappingError);
});

test("inspects nested response fields and limits the sample inventory", () => {
  const inspected = inspectResponse({ games: [{ id: 1, name: "A" }, { id: 2, name: "B" }] });
  assert.equal(inspected.rootType, "object");
  assert.ok(inspected.fields.some(field => field.path === "/games/0/name"));
});

test("enforces timeout and caller cancellation while streaming a response body", async () => {
  const slowBody = (_url, init) => Promise.resolve(new Response(new ReadableStream({
    start(controller) {
      const fail = () => controller.error(new Error("aborted"));
      if (init.signal.aborted) fail();
      else init.signal.addEventListener("abort", fail, { once: true });
    }
  }), { headers: { "content-type": "application/json" } }));
  await assert.rejects(
    fetchJson({ url: "https://a.example/data", limits: { timeoutMs: 250, retries: 0 } }, slowBody),
    e => e.code === "timeout"
  );
  const controller = new AbortController();
  const pending = fetchJson({ url: "https://a.example/data", signal: controller.signal, limits: { retries: 0 } }, slowBody);
  controller.abort();
  await assert.rejects(pending, e => e.code === "cancelled");
});



test("rejects malformed mapping definitions and excessive inspector limits", () => {
  assert.throws(() => mapFields({ value: 1 }, [null]), e => e.code === "invalid_mapping");
  assert.throws(() => mapFields({ value: 1 }, [{ field: "value", source: "/value", type: "any", transforms: ["eval"] }]), e => e.code === "invalid_mapping");
  assert.throws(() => inspectResponse({ value: 1 }, 0), e => e.code === "invalid_request");
});
