import { startLauncher } from "./shared/app.mjs";

const root = document.querySelector("#launcher-root");
const status = document.querySelector("#status");

startLauncher({
  projectUrl: "./fixtures/sample-project.json",
  root,
  onAction: (action) => { status.textContent = `Preview action requested: ${JSON.stringify(action)}`; },
}).catch((error) => {
  status.textContent = `Preview failed: ${error.message}`;
  root.textContent = "Project preview could not be loaded.";
});
