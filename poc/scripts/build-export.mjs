import { mkdir, readFile, realpath, rm, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { parseProjectText } from "../shared/contract.mjs";
import { validateWindowsIcon } from "./lib/windows-icon.mjs";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");
const projectText = await readFile(path.join(root, "fixtures/sample-project.json"), "utf8");
const project = parseProjectText(projectText);
const projectAssetsRoot = await realpath(path.join(root, "assets"));

await rm(dist, { recursive: true, force: true });
await mkdir(path.join(dist, "assets"), { recursive: true });
await mkdir(dist, { recursive: true });
await writeFile(path.join(dist, "index.html"), await readFile(path.join(root, "runtime.html")));
await writeFile(path.join(dist, "runtime.mjs"), await readFile(path.join(root, "runtime.mjs")));
await mkdir(path.join(dist, "shared"), { recursive: true });
for (const filename of ["app.mjs", "contract.mjs", "renderer.mjs", "styles.css"]) {
  await writeFile(path.join(dist, "shared", filename), await readFile(path.join(root, "shared", filename)));
}

const assetManifest = [];
for (const asset of project.assets) {
  const sourcePath = await realpath(path.join(root, asset.path));
  const relative = path.relative(projectAssetsRoot, sourcePath);
  if (!relative || relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    throw new Error(`Asset ${asset.id} resolves outside the project assets directory.`);
  }

  const bytes = await readFile(sourcePath);
  if (asset.kind === "applicationIcon") validateWindowsIcon(bytes);
  const destination = path.join(dist, asset.path);
  await mkdir(path.dirname(destination), { recursive: true });
  await writeFile(destination, bytes);
  assetManifest.push({
    id: asset.id,
    kind: asset.kind,
    path: asset.path,
    sha256: createHash("sha256").update(bytes).digest("hex"),
  });
}

assetManifest.sort((left, right) => left.id < right.id ? -1 : left.id > right.id ? 1 : 0);
const assetManifestSha256 = createHash("sha256").update(JSON.stringify(assetManifest)).digest("hex");
const appIconAsset = assetManifest.find((asset) => asset.id === project.window.iconAssetId);
if (!appIconAsset || appIconAsset.kind !== "applicationIcon") {
  throw new Error("The project window icon is not present in the resolved asset manifest.");
}

await writeFile(path.join(dist, "project.json"), projectText, "utf8");
await writeFile(path.join(dist, "BUILD-METADATA.json"), `${JSON.stringify({
  format: "launchforge.export",
  buildContractVersion: 1,
  projectSchemaVersion: project.schemaVersion,
  renderer: "shared-dom-v1",
  projectId: project.projectId,
  assetManifest,
  assetManifestSha256,
  applicationIconAssetId: appIconAsset.id,
  applicationIconSha256: appIconAsset.sha256,
}, null, 2)}\n`, "utf8");
console.log(`Exported renderer fixture to ${dist}`);
