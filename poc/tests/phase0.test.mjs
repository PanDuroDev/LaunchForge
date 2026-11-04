import test from "node:test";
import assert from "node:assert/strict";
import { readFile, readdir, rm, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseProjectText, validateAssetPath, validateProject, ProjectValidationError } from "../shared/contract.mjs";
import { mountProject, renderProjectMarkup } from "../shared/renderer.mjs";
import { validateWindowsIcon, REQUIRED_WINDOWS_ICO_SIZES } from "../scripts/lib/windows-icon.mjs";

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

test("project requires a dedicated applicationIcon asset reference", () => {
  const missing = structuredClone(fixture);
  delete missing.window.iconAssetId;
  expectCode(() => validateProject(missing), "MISSING_FIELD");

  const wrongKind = structuredClone(fixture);
  wrongKind.window.iconAssetId = wrongKind.assets.find((asset) => asset.kind === "image").id;
  expectCode(() => validateProject(wrongKind), "INVALID_APP_ICON");

  const wrongPath = structuredClone(fixture);
  const icon = wrongPath.assets.find((asset) => asset.id === wrongPath.window.iconAssetId);
  icon.path = "assets/launcher-icon.png";
  expectCode(() => validateProject(wrongPath), "INVALID_APP_ICON_PATH");
});

test("application ICO contains every required Windows icon layer", async () => {
  const asset = fixture.assets.find((entry) => entry.id === fixture.window.iconAssetId);
  const bytes = await readFile(path.join(root, asset.path));
  assert.equal(validateWindowsIcon(bytes), true);
  assert.deepEqual([...REQUIRED_WINDOWS_ICO_SIZES], [16, 24, 32, 48, 64, 256]);
  const count = bytes.readUInt16LE ? bytes.readUInt16LE(4) : (bytes[4] | (bytes[5] << 8));
  let lastImageEnd = 0;
  for (let index = 0; index < count; index += 1) {
    const offset = 6 + index * 16;
    const imageBytes = bytes.readUInt32LE ? bytes.readUInt32LE(offset + 8) :
      (bytes[offset + 8] | (bytes[offset + 9] << 8) | (bytes[offset + 10] << 16) | (bytes[offset + 11] << 24)) >>> 0;
    const imageOffset = bytes.readUInt32LE ? bytes.readUInt32LE(offset + 12) :
      (bytes[offset + 12] | (bytes[offset + 13] << 8) | (bytes[offset + 14] << 16) | (bytes[offset + 15] << 24)) >>> 0;
    lastImageEnd = Math.max(lastImageEnd, imageOffset + imageBytes);
  }
  assert.throws(() => validateWindowsIcon(bytes.subarray(0, lastImageEnd - 1)));
});

test("Tauri receives the exact application icon asset referenced by the project", async () => {
  const result = spawnSync(process.execPath, [path.join(root, "scripts/prepare-tauri-icon.mjs")], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  const source = await readFile(path.join(root, "assets/launcher-icon.ico"));
  const staged = await readFile(path.join(root, "src-tauri/icons/icon.ico"));
  assert.equal(hash(source), hash(staged));
});

test("unknown schema versions fail closed", () => {
  const invalid = structuredClone(fixture);
  invalid.schemaVersion = 2;
  expectCode(() => validateProject(invalid), "UNSUPPORTED_SCHEMA_VERSION");
});

test("UUIDv4 identifiers are lowercase and unique across project entities", () => {
  const invalid = structuredClone(fixture);
  invalid.components[0].children[0].id = invalid.assets[0].id;
  expectCode(() => validateProject(invalid), "DUPLICATE_ID");

  const uppercase = structuredClone(fixture);
  uppercase.projectId = "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF";
  expectCode(() => validateProject(uppercase), "INVALID_ID");
});

test("root must be a container and asset paths are unique case-insensitively", () => {
  const wrongRoot = structuredClone(fixture);
  wrongRoot.components[0] = structuredClone(wrongRoot.components[0].children[0]);
  expectCode(() => validateProject(wrongRoot), "INVALID_ROOT_COMPONENT");

  const duplicatePath = structuredClone(fixture);
  duplicatePath.assets.push({
    id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
    kind: "image",
    path: "assets/SAMPLE-COVER.svg",
  });
  expectCode(() => validateProject(duplicatePath), "DUPLICATE_ASSET_PATH");
});

test("minimum window bounds cannot exceed the default dimensions", () => {
  const tooWide = structuredClone(fixture);
  tooWide.window.minWidth = tooWide.window.width + 1;
  expectCode(() => validateProject(tooWide), "INVALID_NUMBER");

  const tooTall = structuredClone(fixture);
  tooTall.window.minHeight = tooTall.window.height + 1;
  expectCode(() => validateProject(tooTall), "INVALID_NUMBER");
});

test("asset paths reject traversal, drive syntax, alternate streams, and device names", () => {
  for (const value of ["../secret.txt", "assets/../../secret.txt", "C:/secret.txt", "assets/file:stream.svg", "assets/NUL.svg", "assets/%2e%2e.svg", "assets\\cover.svg", "assets/file."]) {
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
  const unreferencedPath = path.join(root, "assets/unreferenced-phase0-test.txt");
  await writeFile(unreferencedPath, "This file is deliberately not declared in the project.");
  let result;
  try {
    result = spawnSync(process.execPath, [path.join(root, "scripts/build-export.mjs")], { encoding: "utf8" });
  } finally {
    await rm(unreferencedPath, { force: true });
  }
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
  const exportedIcon = await readFile(path.join(root, "dist/assets/launcher-icon.ico"));
  const sourceIcon = await readFile(path.join(root, "assets/launcher-icon.ico"));
  assert.equal(hash(exportedIcon), hash(sourceIcon));
  const metadata = JSON.parse(await readFile(path.join(root, "dist/BUILD-METADATA.json"), "utf8"));
  const expectedManifest = await Promise.all(fixture.assets.map(async (asset) => ({
    id: asset.id,
    kind: asset.kind,
    path: asset.path,
    sha256: hash(await readFile(path.join(root, asset.path))),
  })));
  expectedManifest.sort((left, right) => left.id < right.id ? -1 : left.id > right.id ? 1 : 0);
  assert.deepEqual(metadata.assetManifest, expectedManifest);
  assert.equal(metadata.assetManifestSha256, hash(JSON.stringify(expectedManifest)));
  assert.equal(metadata.applicationIconAssetId, fixture.window.iconAssetId);
  assert.equal(metadata.applicationIconSha256, hash(sourceIcon));
  const exportedAssetFiles = await readdir(path.join(root, "dist/assets"));
  assert.deepEqual(exportedAssetFiles.sort(), fixture.assets.map((asset) => path.basename(asset.path)).sort());
  assert.equal(exportedAssetFiles.includes("unreferenced-phase0-test.txt"), false);
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
