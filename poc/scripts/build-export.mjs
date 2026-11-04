import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");
const projectText = await readFile(path.join(root, "fixtures/sample-project.json"), "utf8");
const project = JSON.parse(projectText);

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });
await cp(path.join(root, "runtime.html"), path.join(dist, "index.html"));
await cp(path.join(root, "runtime.mjs"), path.join(dist, "runtime.mjs"));
await cp(path.join(root, "shared"), path.join(dist, "shared"), { recursive: true });
await cp(path.join(root, "assets"), path.join(dist, "assets"), { recursive: true });
await writeFile(path.join(dist, "project.json"), projectText, "utf8");
await writeFile(path.join(dist, "BUILD-METADATA.json"), `${JSON.stringify({
  format: "launchforge.export",
  buildContractVersion: 1,
  projectSchemaVersion: project.schemaVersion,
  renderer: "shared-dom-v1",
  projectId: project.projectId,
}, null, 2)}\n`, "utf8");
console.log(`Exported renderer fixture to ${dist}`);
