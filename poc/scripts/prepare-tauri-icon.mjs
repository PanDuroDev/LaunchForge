import { createHash } from "node:crypto";
import { mkdir, readFile, realpath, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseProjectText } from "../shared/contract.mjs";
import { validateWindowsIcon } from "./lib/windows-icon.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const project = parseProjectText(await readFile(path.join(root, "fixtures/sample-project.json"), "utf8"));
const asset = project.assets.find((entry) => entry.id === project.window.iconAssetId);
if (!asset || asset.kind !== "applicationIcon") throw new Error("The project window must reference an applicationIcon asset.");

const assetsRoot = await realpath(path.join(root, "assets"));
const sourcePath = await realpath(path.join(root, asset.path));
const relative = path.relative(assetsRoot, sourcePath);
if (!relative || relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
  throw new Error("Application icon resolves outside the project assets directory.");
}

const bytes = await readFile(sourcePath);
validateWindowsIcon(bytes);
const destination = path.join(root, "src-tauri", "icons", "icon.ico");
await mkdir(path.dirname(destination), { recursive: true });
await writeFile(destination, bytes);
console.log(`Prepared application icon ${asset.id} (${createHash("sha256").update(bytes).digest("hex")}).`);
