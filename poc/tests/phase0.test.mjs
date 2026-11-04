import test from "node:test";
import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseProjectText, validateAssetPath, validateProject, ProjectValidationError } from "../shared/contract.mjs";
import { mountProject, renderProjectMarkup } from "../shared/renderer.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const fixtureText = await readFile(path.join(root, "fixtures/sample-project.json"), "utf8");
const fixture = parseProjectText(fixtureText);

function expectCode(callback, code) {
  assert.throws(callback, (error) => error instanceof ProjectValidationError && error.code === code);
}

function hash(value) {
  return createHash("sha256").update(value).digest("hex");
}

test("sample project validates as schema v1", () => {
  assert.equal(validateProject(fixture), true);
});

test("project parser rejects malformed JSON and oversized inputs", () => {
  expectCode(() => parseProjectText("{"), "INVALID_JSON");
  expectCode(() => parseProjectText(" ".repeat(1024 * 1024 + 1)), "PROJECT_TOO_LARGE");
});

test("unknown schema versions fail closed", () => {
  const invalid = structuredClone(fixture);
  invalid.schemaVersion = 2;
  expectCode(() => validateProject(invalid), "UNSUPPORTED_SCHEMA_VERSION");
});

test("IDs are stable UUIDv4 values and unique across project entities", () => {
  const invalid = structuredClone(fixture);
  invalid.components[0].children[0].id = invalid.assets[0].id;
  expectCode(() => validateProject(invalid), "DUPLICATE_ID");
});

test("asset paths reject traversal, drive syntax, alternate streams, and device names", () => {
  for (const value of ["../secret.txt", "assets/../../secret.txt", "C:/secret.txt", "assets/file:stream.svg", "assets/NUL.svg", "assets/%2e%2e.svg", "assets\\cover.svg"]) {
    expectCode(() => validateAssetPath(value), "UNSAFE_ASSET_PATH");
  }
  assert.equal(validateAssetPath("assets/cover-01.svg"), "assets/cover-01.svg");
});

test("unknown components and arbitrary actions are rejected", () => {
  const badComponent = structuredClone(fixture);
  badComponent.components[0].children[0].type = "customScript";
  expectCode(() => validateProject(badComponent), "UNSUPPORTED_COMPONENT");

  const badAction = structuredClone(fixture);
  badAction.components[0].children.at(-1).props.action = { type: "runCommand", command: "whoami" };
  expectCode(() => validateProject(badAction), "UNSUPPORTED_ACTION");

  const unknownField = structuredClone(fixture);
  unknownField.hostCommand = "whoami";
  expectCode(() => validateProject(unknownField), "UNKNOWN_FIELD");
});

test("text and project-controlled labels are HTML escaped", () => {
  const malicious = structuredClone(fixture);
  malicious.components[0].children[0].props.value = "<script>alert(1)</script>&\"";
  const html = renderProjectMarkup(malicious);
  assert.equal(html.includes("<script>"), false);
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;&amp;&quot;/);
});

test("local game binding resolves from project data", () => {
  const html = renderProjectMarkup(fixture);
  assert.match(html, /Sample Game/);
  assert.match(html, /data-lf-action="navigate" data-lf-target="library"/);
  assert.match(html, /data-lf-action="launchGame" data-lf-game-id="33333333-3333-4333-8333-333333333333"/);
  assert.match(html, /assets\/sample-cover\.svg/);
});

test("preview and exported package use byte-identical renderer and project contracts", async () => {
  const result = spawnSync(process.execPath, [path.join(root, "scripts/build-export.mjs")], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr || result.stdout);

  const sourceRenderer = await readFile(path.join(root, "shared/renderer.mjs"));
  const exportedRenderer = await readFile(path.join(root, "dist/shared/renderer.mjs"));
  const sourceContract = await readFile(path.join(root, "shared/contract.mjs"));
  const exportedContract = await readFile(path.join(root, "dist/shared/contract.mjs"));
  const sourceProject = await readFile(path.join(root, "fixtures/sample-project.json"));
  const exportedProject = await readFile(path.join(root, "dist/project.json"));

  assert.equal(hash(sourceRenderer), hash(exportedRenderer));
  assert.equal(hash(sourceContract), hash(exportedContract));
  assert.equal(hash(sourceProject), hash(exportedProject));

  const exportedModuleUrl = new URL(`file://${path.join(root, "dist/shared/renderer.mjs").replaceAll("\\", "/")}`);
  const exportedRendererModule = await import(exportedModuleUrl.href);
  assert.equal(exportedRendererModule.renderProjectMarkup(JSON.parse(exportedProject.toString("utf8"))), renderProjectMarkup(fixture));

  const distFiles = await readdir(path.join(root, "dist"));
  assert.ok(distFiles.includes("index.html"));
  assert.ok(distFiles.includes("runtime.mjs"));
  assert.ok(distFiles.includes("BUILD-METADATA.json"));
});


test("renderer dispatches only typed navigation and game-ID actions", () => {
  const listeners = new Map();
  const root = {
    innerHTML: "",
    addEventListener: (name, callback) => listeners.set(name, callback),
    removeEventListener: (name) => listeners.delete(name),
    contains: () => true,
  };
  const received = [];
  const dispose = mountProject(root, fixture, (action) => received.push(action));
  const onClick = listeners.get("click");
  onClick({ target: { closest: (selector) => selector === "[data-lf-action]" ? { dataset: { lfAction: "launchGame", lfGameId: fixture.games[0].id } } : null } });
  onClick({ target: { closest: (selector) => selector === "[data-lf-action]" ? { dataset: { lfAction: "navigate", lfTarget: "library" } } : null } });
  assert.deepEqual(received, [
    { type: "launchGame", gameId: fixture.games[0].id },
    { type: "navigate", target: "library" },
  ]);
  dispose();
  assert.equal(listeners.has("click"), false);
});
