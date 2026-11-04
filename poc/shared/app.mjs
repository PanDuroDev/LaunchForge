import { parseProjectText } from "./contract.mjs";
import { mountProject } from "./renderer.mjs";

export async function startLauncher({ projectUrl, root, onAction }) {
  const response = await fetch(projectUrl, { cache: "no-store", credentials: "same-origin" });
  if (!response.ok) throw new Error(`Unable to load project (${response.status})`);
  const project = parseProjectText(await response.text());
  const dispose = mountProject(root, project, onAction);
  return { project, dispose };
}
