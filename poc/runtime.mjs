import { startLauncher } from "./shared/app.mjs";

const root = document.querySelector("#launcher-root");
const status = document.querySelector("#status");

startLauncher({
  projectUrl: "./project.json",
  root,
  onAction: (action) => { status.textContent = `Runtime action requested: ${JSON.stringify(action)}`; },
}).catch((error) => {
  status.textContent = `Runtime failed: ${error.message}`;
  root.textContent = "Exported project could not be loaded.";
});
