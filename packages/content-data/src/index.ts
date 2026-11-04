export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type BindingType = "string" | "number" | "boolean" | "string[]" | "object" | "any";
export type Transform = "trim" | "lowercase" | "uppercase" | "toNumber" | "toBoolean" | "toUrl";
export interface NetworkLimits { timeoutMs: number; maxBytes: number; maxRedirects: number; retries: number; retryBaseDelayMs: number; }
export const DEFAULT_LIMITS: Readonly<NetworkLimits> = Object.freeze({ timeoutMs: 10000, maxBytes: 1048576, maxRedirects: 3, retries: 2, retryBaseDelayMs: 150 });

export class ContentError extends Error {
  constructor(readonly code: string, message: string, readonly status?: number) { super(message); this.name = "ContentError"; }
}
export class MappingError extends Error {
  constructor(readonly field: string, readonly code: string, message: string) { super(message); this.name = "MappingError"; }
}
function limitsOf(value: Partial<NetworkLimits> = {}): NetworkLimits {
  const v = { ...DEFAULT_LIMITS, ...value };
  if (!Number.isInteger(v.timeoutMs) || v.timeoutMs < 250 || v.timeoutMs > 60000 ||
      !Number.isInteger(v.maxBytes) || v.maxBytes < 1 || v.maxBytes > 10485760 ||
      !Number.isInteger(v.maxRedirects) || v.maxRedirects < 0 || v.maxRedirects > 5 ||
      !Number.isInteger(v.retries) || v.retries < 0 || v.retries > 3 ||
      !Number.isInteger(v.retryBaseDelayMs) || v.retryBaseDelayMs < 0 || v.retryBaseDelayMs > 2000) {
    throw new ContentError("invalid_request", "Network limits are outside the supported bounds");
  }
  return v;
}
const secretQuery = /^(?:api[-_]?key|key|token|access[-_]?token|refresh[-_]?token|secret|password|signature|authorization|client[-_]?secret)$/i;
export function validateHttpsEndpoint(value: string): URL {
  let url: URL;
  try { url = new URL(value); } catch { throw new ContentError("invalid_url", "The endpoint URL is invalid"); }
  if (url.protocol !== "https:") throw new ContentError("insecure_url", "Only HTTPS endpoints are supported");
  if (url.username || url.password) throw new ContentError("invalid_url", "Credentials must not be embedded in endpoint URLs");
  for (const key of url.searchParams.keys()) {
    if (secretQuery.test(key.replace(/[^a-z0-9_-]/gi, ""))) throw new ContentError("invalid_url", "Credential query parameters are not allowed");
  }
  return url;
}
function validateJson(value: unknown): asserts value is JsonValue {
  const stack: Array<{ value: unknown; depth: number }> = [{ value, depth: 0 }];
  let seen = 0;
  while (stack.length) {
    const item = stack.pop()!;
    if (++seen > 100000 || item.depth > 64) throw new ContentError("invalid_json_structure", "The JSON payload exceeds structural limits");
    const v = item.value;
    if (v === null || typeof v === "string" || typeof v === "boolean") continue;
    if (typeof v === "number") { if (!Number.isFinite(v)) throw new ContentError("invalid_json_structure", "Non-finite JSON number"); continue; }
    if (Array.isArray(v)) { for (const child of v) stack.push({ value: child, depth: item.depth + 1 }); continue; }
    if (typeof v !== "object" || Object.getPrototypeOf(v) !== Object.prototype) throw new ContentError("invalid_json_structure", "Only plain JSON objects are supported");
    for (const [key, child] of Object.entries(v)) {
      if (["__proto__", "prototype", "constructor"].includes(key)) throw new ContentError("invalid_json_structure", "Prototype-sensitive JSON property");
      stack.push({ value: child, depth: item.depth + 1 });
    }
  }
}
async function readLimited(response: Response, max: number): Promise<Uint8Array> {
  const length = response.headers.get("content-length");
  if (length && /^\d+$/.test(length) && Number(length) > max) {
    await response.body?.cancel();
    throw new ContentError("response_too_large", "JSON response exceeds the configured size limit");
  }
  if (!response.body) return new Uint8Array();
  const reader = response.body.getReader(), chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      total += part.value.byteLength;
      if (total > max) { await reader.cancel(); throw new ContentError("response_too_large", "JSON response exceeds the configured size limit"); }
      chunks.push(part.value);
    }
  } finally { reader.releaseLock(); }
  const result = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.byteLength; }
  return result;
}
const redirects = new Set([301, 302, 303, 307, 308]);
const retryStatuses = new Set([408, 425, 429, 500, 502, 503, 504]);
const secretHeader = /authorization|cookie|token|secret|password|credential|api[-_]?key/i;
function delay(ms: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.reject(new ContentError("cancelled", "Request cancelled"));
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { signal?.removeEventListener("abort", abort); resolve(); }, ms);
    const abort = () => { clearTimeout(timer); signal?.removeEventListener("abort", abort); reject(new ContentError("cancelled", "Request cancelled")); };
    signal?.addEventListener("abort", abort, { once: true });
  });
}
/** HTTPS GET JSON adapter with bounded redirects, streamed bytes, timeout, cancellation and retries. */
export async function fetchJson(
  request: { url: string; method?: "GET"; headers?: HeadersInit; signal?: AbortSignal; limits?: Partial<NetworkLimits> },
  fetchImpl: typeof fetch = fetch
): Promise<JsonValue> {
  if (request.method && request.method !== "GET") throw new ContentError("invalid_request", "Only GET is supported");
  const initial = validateHttpsEndpoint(request.url), limits = limitsOf(request.limits);
  let headers: Headers;
  try { headers = new Headers(request.headers); } catch { throw new ContentError("invalid_request", "Invalid request headers"); }
  headers.set("accept", "application/json, application/*+json");
  for (let attempt = 0; attempt <= limits.retries; attempt++) {
    if (request.signal?.aborted) throw new ContentError("cancelled", "Request cancelled");
    const controller = new AbortController();
    let timedOut = false;
    const relay = () => controller.abort();
    request.signal?.addEventListener("abort", relay, { once: true });
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, limits.timeoutMs);
    try {
      let url = new URL(initial), response: Response | undefined;
      for (let count = 0; count <= limits.maxRedirects; count++) {
        response = await fetchImpl(url, {
          method: "GET", headers, signal: controller.signal, redirect: "manual",
          credentials: "omit", cache: "no-store", referrerPolicy: "no-referrer"
        });
        if (!redirects.has(response.status)) break;
        const location = response.headers.get("location");
        await response.body?.cancel();
        if (!location || count === limits.maxRedirects) throw new ContentError("redirect_rejected", "Redirect limit exceeded");
        let next: URL;
        try { next = new URL(location, url); } catch { throw new ContentError("redirect_rejected", "Invalid redirect location"); }
        validateHttpsEndpoint(next.toString());
        if (next.origin !== initial.origin) throw new ContentError("redirect_rejected", "Cross-origin redirects are not permitted");
        for (const name of Array.from(headers.keys())) if (secretHeader.test(name)) headers.delete(name);
        url = next;
      }
      if (!response) throw new ContentError("network_error", "Endpoint unavailable");
      if (!response.ok) {
        const status = response.status;
        await response.body?.cancel();
        if (retryStatuses.has(status) && attempt < limits.retries) {
          const retryHeader = response.headers.get("retry-after");
          const retryAfter = retryHeader === null ? Number.NaN : Number(retryHeader);
          const wait = Number.isFinite(retryAfter) && retryAfter >= 0 ? Math.min(retryAfter * 1000, 5000) : Math.min(limits.retryBaseDelayMs * 2 ** attempt, 2000);
          clearTimeout(timer); request.signal?.removeEventListener("abort", relay);
          await delay(wait, request.signal); continue;
        }
        throw new ContentError("http_error", "Endpoint returned HTTP " + status, status);
      }
      const media = (response.headers.get("content-type") ?? "").split(";", 1)[0]!.trim().toLowerCase();
      if (media !== "application/json" && !(media.startsWith("application/") && media.endsWith("+json"))) {
        await response.body?.cancel(); throw new ContentError("invalid_content_type", "Endpoint did not return JSON");
      }
      const bytes = await readLimited(response, limits.maxBytes);
      let parsed: unknown;
      try { parsed = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)); }
      catch { throw new ContentError("invalid_json", "Endpoint returned malformed UTF-8 JSON"); }
      validateJson(parsed);
      return parsed;
    } catch (error) {
      if (error instanceof ContentError) {
        if (error.code === "network_error" && attempt < limits.retries) {
          clearTimeout(timer); request.signal?.removeEventListener("abort", relay);
          await delay(Math.min(limits.retryBaseDelayMs * 2 ** attempt, 2000), request.signal); continue;
        }
        throw error;
      }
      if (request.signal?.aborted) throw new ContentError("cancelled", "Request cancelled");
      if (timedOut) throw new ContentError("timeout", "Endpoint timed out");
      if (attempt < limits.retries) {
        clearTimeout(timer); request.signal?.removeEventListener("abort", relay);
        await delay(Math.min(limits.retryBaseDelayMs * 2 ** attempt, 2000), request.signal); continue;
      }
      throw new ContentError("network_error", "Endpoint could not be reached");
    } finally { clearTimeout(timer); request.signal?.removeEventListener("abort", relay); }
  }
  throw new ContentError("network_error", "Endpoint could not be reached after retries");
}

export interface FieldMapping {
  field: string; source: string; type: BindingType; optional?: boolean; defaultValue?: JsonValue; transforms?: Transform[];
}
const blocked = new Set(["__proto__", "prototype", "constructor"]);
function atPointer(root: JsonValue, pointer: string, field: string): JsonValue | undefined {
  if (pointer === "") return root;
  if (!pointer.startsWith("/")) throw new MappingError(field, "invalid_mapping", "Source must be an RFC 6901 JSON Pointer");
  let value: JsonValue | undefined = root;
  for (const raw of pointer.slice(1).split("/")) {
    if (/~(?![01])/.test(raw)) throw new MappingError(field, "invalid_mapping", "Invalid JSON Pointer escape");
    const key = raw.replace(/~1/g, "/").replace(/~0/g, "~");
    if (blocked.has(key)) throw new MappingError(field, "invalid_mapping", "Prototype-sensitive path");
    if (Array.isArray(value)) value = /^(0|[1-9]\d*)$/.test(key) ? value[Number(key)] : undefined;
    else if (value !== null && typeof value === "object" && Object.hasOwn(value, key)) value = value[key];
    else return undefined;
  }
  return value;
}
function transform(value: JsonValue, name: Transform, field: string): JsonValue {
  try {
    switch (name) {
      case "trim": if (typeof value !== "string") throw 0; return value.trim();
      case "lowercase": if (typeof value !== "string") throw 0; return value.toLowerCase();
      case "uppercase": if (typeof value !== "string") throw 0; return value.toUpperCase();
      case "toNumber": { const n = typeof value === "number" ? value : typeof value === "string" && value.trim() ? Number(value) : NaN; if (!Number.isFinite(n)) throw 0; return n; }
      case "toBoolean": if (value === true || value === "true") return true; if (value === false || value === "false") return false; throw 0;
      case "toUrl": if (typeof value !== "string") throw 0; return validateHttpsEndpoint(value).toString();
    }
  } catch { throw new MappingError(field, "transform_failed", "Safe transformation failed"); }
}
function typeMatches(value: JsonValue, type: BindingType): boolean {
  if (type === "any") return true;
  if (type === "string[]") return Array.isArray(value) && value.every(x => typeof x === "string");
  if (type === "object") return value !== null && typeof value === "object" && !Array.isArray(value);
  if (type === "number") return typeof value === "number" && Number.isFinite(value);
  return typeof value === type;
}
/** Typed JSON Pointer field mapping with safe defaults and transformation allowlist. */
export function mapFields<T extends Record<string, JsonValue> = Record<string, JsonValue>>(input: JsonValue, mappings: readonly FieldMapping[]): T {
  validateJson(input);
  const output = Object.create(null) as Record<string, JsonValue>, seen = new Set<string>();
  for (const m of mappings) {
    if (!/^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(m.field) || blocked.has(m.field) || seen.has(m.field)) throw new MappingError(m.field, "invalid_mapping", "Invalid or duplicate output field");
    seen.add(m.field);
    let value = atPointer(input, m.source, m.field);
    if (value === undefined || value === null) {
      if (m.defaultValue !== undefined) value = m.defaultValue;
      else if (m.optional) continue;
      else throw new MappingError(m.field, "missing_value", "Required source value is missing");
    }
    for (const step of m.transforms ?? []) value = transform(value, step, m.field);
    if (!typeMatches(value, m.type)) throw new MappingError(m.field, "type_mismatch", "Mapped value does not match declared type");
    output[m.field] = value;
  }
  return output as T;
}

export interface InspectedField { path: string; type: string; heterogeneous?: boolean; }
export function inspectResponse(input: JsonValue, maxFields = 500): { rootType: string; fields: InspectedField[]; truncated: boolean } {
  const kinds = new Map<string, Set<string>>(), stack: Array<{ value: JsonValue; path: string; depth: number }> = [{ value: input, path: "", depth: 0 }];
  let truncated = false;
  while (stack.length && kinds.size <= maxFields) {
    const item = stack.pop()!, value = item.value;
    const kind = value === null ? "null" : Array.isArray(value) ? "array" : typeof value;
    const values = kinds.get(item.path) ?? new Set<string>(); values.add(kind); kinds.set(item.path, values);
    if (item.depth >= 8) { if (kind === "object" || kind === "array") truncated = true; continue; }
    if (Array.isArray(value)) {
      value.slice(0, 5).forEach((child, index) => stack.push({ value: child, path: item.path + "/" + index, depth: item.depth + 1 }));
      if (value.length > 5) truncated = true;
    } else if (value !== null && typeof value === "object") {
      for (const [key, child] of Object.entries(value)) if (!blocked.has(key)) stack.push({ value: child, path: item.path + "/" + key.replace(/~/g,"~0").replace(/\//g,"~1"), depth: item.depth + 1 });
    }
  }
  if (kinds.size > maxFields) truncated = true;
  return { rootType: input === null ? "null" : Array.isArray(input) ? "array" : typeof input,
    fields: Array.from(kinds, ([path, set]) => ({ path, type: Array.from(set)[0]!, ...(set.size > 1 ? { heterogeneous: true } : {}) })).slice(0, maxFields).sort((a,b) => a.path.localeCompare(b.path)), truncated };
}

