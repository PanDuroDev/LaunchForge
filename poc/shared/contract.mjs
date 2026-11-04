export const PROJECT_FORMAT = "launchforge.project";
export const PROJECT_SCHEMA_VERSION = 1;
export const MAX_PROJECT_BYTES = 1024 * 1024;
export const MAX_COMPONENTS = 128;
export const MAX_COMPONENT_DEPTH = 16;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const HEX = /^#[0-9a-f]{6}$/i;
const TOKENS = new Set(["surface", "text", "accent"]);
const TYPES = new Set(["container", "text", "image", "button", "gameCard"]);
const NAV = new Set(["home", "library"]);
const RESERVED = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$/i;

export class ProjectValidationError extends Error {
  constructor(code, message, path = "$") {
    super(message); this.name = "ProjectValidationError"; this.code = code; this.path = path;
  }
}
const fail = (code, message, path) => { throw new ProjectValidationError(code, message, path); };
const record = value => value !== null && typeof value === "object" && !Array.isArray(value);
function keys(value, allowed, required, path) {
  for (const key of Object.keys(value)) if (!allowed.includes(key)) fail("UNKNOWN_FIELD", `Unknown field: ${key}`, `${path}.${key}`);
  for (const key of required) if (!Object.hasOwn(value, key)) fail("MISSING_FIELD", `Missing required field: ${key}`, `${path}.${key}`);
}
function str(value, path, max, empty = false) {
  if (typeof value !== "string" || value.length > max || (!empty && !value.trim())) fail("INVALID_STRING", `Expected a string of at most ${max} characters`, path);
}
function uuid(value, path) { if (typeof value !== "string" || !UUID.test(value)) fail("INVALID_ID", "Expected a stable UUIDv4 identifier", path); }
function integer(value, path, min, max) { if (!Number.isInteger(value) || value < min || value > max) fail("INVALID_NUMBER", `Expected integer from ${min} to ${max}`, path); }

export function validateAssetPath(value, path = "$.assets[].path") {
  str(value, path, 180);
  if (!value.startsWith("assets/") || /[\\:%?]/.test(value)) fail("UNSAFE_ASSET_PATH", "Asset paths must be plain relative paths under assets/", path);
  const parts = value.split("/");
  if (parts.length !== 2 || parts[0] !== "assets" || !/^(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9._-]{0,118}[a-zA-Z0-9_-])$/.test(parts[1]) || RESERVED.test(parts[1])) fail("UNSAFE_ASSET_PATH", "Asset path must contain one portable filename under assets/", path);
  return value;
}
function binding(value, games, path) {
  if (!record(value) || value.source !== "game") fail("INVALID_BINDING", "Only local game bindings are supported", path);
  uuid(value.gameId, `${path}.gameId`);
  if (!games.has(value.gameId)) fail("MISSING_GAME", "Binding references an unknown game", `${path}.gameId`);
  if (!["title", "description"].includes(value.field)) fail("INVALID_BINDING", "Only game.title and game.description bindings are supported", `${path}.field`);
}

export function validateProject(project) {
  if (!record(project)) fail("INVALID_PROJECT", "Project root must be an object", "$");
  const top = ["format", "schemaVersion", "projectId", "name", "window", "theme", "assets", "games", "components"];
  keys(project, top, top, "$"
  );
  if (project.format !== PROJECT_FORMAT) fail("UNSUPPORTED_FORMAT", `Expected format ${PROJECT_FORMAT}`, "$.format");
  if (project.schemaVersion !== PROJECT_SCHEMA_VERSION) fail("UNSUPPORTED_SCHEMA_VERSION", `Only schema version ${PROJECT_SCHEMA_VERSION} is supported`, "$.schemaVersion");
  uuid(project.projectId, "$.projectId"); str(project.name, "$.name", 80);

  const w = project.window, wk = ["title", "iconAssetId", "width", "height", "minWidth", "minHeight", "resizable"];
  if (!record(w)) fail("INVALID_WINDOW", "Window settings are required", "$.window");
  keys(w, wk, wk, "$.window"); str(w.title, "$.window.title", 80); uuid(w.iconAssetId, "$.window.iconAssetId");
  integer(w.width, "$.window.width", 320, 4096); integer(w.height, "$.window.height", 240, 2160);
  integer(w.minWidth, "$.window.minWidth", 320, w.width); integer(w.minHeight, "$.window.minHeight", 240, w.height);
  if (typeof w.resizable !== "boolean") fail("INVALID_WINDOW", "resizable must be boolean", "$.window.resizable");

  if (!record(project.theme)) fail("INVALID_THEME", "Theme tokens are required", "$.theme");
  keys(project.theme, [...TOKENS], [...TOKENS], "$.theme");
  for (const token of TOKENS) if (typeof project.theme[token] !== "string" || !HEX.test(project.theme[token])) fail("INVALID_THEME_TOKEN", `${token} must be #RRGGBB`, `$.theme.${token}`);
  if (!Array.isArray(project.assets) || project.assets.length > 128) fail("INVALID_ASSETS", "assets must be an array of at most 128 entries", "$.assets");
  if (!Array.isArray(project.games) || project.games.length > 16) fail("INVALID_GAMES", "games must be an array of at most 16 entries", "$.games");
  if (!Array.isArray(project.components) || project.components.length !== 1) fail("INVALID_COMPONENTS", "Schema v1 requires exactly one root component", "$.components");
  if (project.components[0]?.type !== "container") fail("INVALID_ROOT_COMPONENT", "The project root component must be a container", "$.components[0].type");

  const ids = new Set([project.projectId]), assets = new Map(), assetPaths = new Set();
  for (const [i, a] of project.assets.entries()) {
    const p = `$.assets[${i}]`;
    if (!record(a)) fail("INVALID_ASSET", "Asset must be an object", p);
    keys(a, ["id", "kind", "path"], ["id", "kind", "path"], p); uuid(a.id, `${p}.id`);
    if (ids.has(a.id)) fail("DUPLICATE_ID", "Entity IDs must be unique", `${p}.id`); ids.add(a.id);
    if (!["image", "applicationIcon"].includes(a.kind)) fail("UNSUPPORTED_ASSET_KIND", "Only image and applicationIcon assets are supported", `${p}.kind`);
    validateAssetPath(a.path, `${p}.path`);
    if (a.kind === "applicationIcon" && !a.path.endsWith(".ico")) fail("INVALID_APP_ICON_PATH", "Application icon assets must use a lowercase .ico file", `${p}.path`);
    if (a.kind === "image" && a.path.toLowerCase().endsWith(".ico")) fail("INVALID_ASSET_KIND", "ICO files must use kind applicationIcon", `${p}.kind`);
    const normalizedAssetPath = a.path.toLowerCase();
    if (assetPaths.has(normalizedAssetPath)) fail("DUPLICATE_ASSET_PATH", "Asset paths must be unique using Windows case-insensitive comparison", `${p}.path`);
    assetPaths.add(normalizedAssetPath); assets.set(a.id, a);
  }
  const appIcon = assets.get(w.iconAssetId);
  if (!appIcon) fail("MISSING_APP_ICON", "window.iconAssetId must reference a project asset", "$.window.iconAssetId");
  if (appIcon.kind !== "applicationIcon") fail("INVALID_APP_ICON", "window.iconAssetId must reference an applicationIcon asset", "$.window.iconAssetId");
  const games = new Map();
  for (const [i, g] of project.games.entries()) {
    const p = `$.games[${i}]`, gk = ["id", "title", "description", "coverAssetId"];
    if (!record(g)) fail("INVALID_GAME", "Game must be an object", p);
    keys(g, gk, gk, p); uuid(g.id, `${p}.id`);
    if (ids.has(g.id)) fail("DUPLICATE_ID", "Entity IDs must be unique", `${p}.id`); ids.add(g.id);
    str(g.title, `${p}.title`, 120); str(g.description, `${p}.description`, 500, true); uuid(g.coverAssetId, `${p}.coverAssetId`);
    if (!assets.has(g.coverAssetId)) fail("MISSING_ASSET", "Game cover references an unknown asset", `${p}.coverAssetId`);
    games.set(g.id, g);
  }
  let count = 0;
  function visit(node, depth, p) {
    if (++count > MAX_COMPONENTS) fail("COMPONENT_LIMIT", `At most ${MAX_COMPONENTS} components are allowed`, p);
    if (depth > MAX_COMPONENT_DEPTH) fail("COMPONENT_DEPTH_LIMIT", `Nesting exceeds ${MAX_COMPONENT_DEPTH}`, p);
    if (!record(node)) fail("INVALID_COMPONENT", "Component must be an object", p);
    const required = node.type === "container" ? ["id", "type", "props", "children"] : ["id", "type", "props"];
    keys(node, required, required, p); uuid(node.id, `${p}.id`);
    if (ids.has(node.id)) fail("DUPLICATE_ID", "Entity IDs must be unique", `${p}.id`); ids.add(node.id);
    if (!TYPES.has(node.type)) fail("UNSUPPORTED_COMPONENT", `Unsupported component type: ${String(node.type)}`, `${p}.type`);
    if (!record(node.props)) fail("INVALID_COMPONENT_PROPS", "Component props must be an object", `${p}.props`);
    if (node.type === "container") {
      const k = ["axis", "gap", "padding", "background"]; keys(node.props, k, k, `${p}.props`);
      if (!["vertical", "horizontal"].includes(node.props.axis)) fail("INVALID_LAYOUT", "Invalid container axis", `${p}.props.axis`);
      integer(node.props.gap, `${p}.props.gap`, 0, 64); integer(node.props.padding, `${p}.props.padding`, 0, 64);
      if (!TOKENS.has(node.props.background)) fail("INVALID_THEME_REFERENCE", "Unknown theme token", `${p}.props.background`);
      if (!Array.isArray(node.children) || node.children.length > 32) fail("INVALID_CHILDREN", "Container children must be an array of at most 32 items", `${p}.children`);
      node.children.forEach((child, i) => visit(child, depth + 1, `${p}.children[${i}]`)); return;
    }
    if (Object.hasOwn(node, "children")) fail("UNEXPECTED_CHILDREN", "Only containers may have children", `${p}.children`);
    if (node.type === "text") {
      const k = ["value", "fontSize", "color"]; keys(node.props, k, k, `${p}.props`);
      if (typeof node.props.value === "string") str(node.props.value, `${p}.props.value`, 500, true); else binding(node.props.value, games, `${p}.props.value`);
      integer(node.props.fontSize, `${p}.props.fontSize`, 12, 48);
      if (!TOKENS.has(node.props.color)) fail("INVALID_THEME_REFERENCE", "Unknown theme token", `${p}.props.color`);
    } else if (node.type === "image") {
      const k = ["assetId", "alt", "fit"]; keys(node.props, k, k, `${p}.props`); uuid(node.props.assetId, `${p}.props.assetId`);
      if (!assets.has(node.props.assetId)) fail("MISSING_ASSET", "Image references an unknown asset", `${p}.props.assetId`);
      str(node.props.alt, `${p}.props.alt`, 120); if (!["cover", "contain"].includes(node.props.fit)) fail("INVALID_IMAGE_FIT", "Image fit must be cover or contain", `${p}.props.fit`);
    } else if (node.type === "button") {
      const k = ["label", "action"]; keys(node.props, k, k, `${p}.props`); str(node.props.label, `${p}.props.label`, 40);
      const a = node.props.action; if (!record(a)) fail("UNSUPPORTED_ACTION", "Action must be an allowlisted object", `${p}.props.action`);
      if (a.type === "navigate") { keys(a, ["type", "target"], ["type", "target"], `${p}.props.action`); if (!NAV.has(a.target)) fail("UNSUPPORTED_ACTION", "Navigation target is not allowlisted", `${p}.props.action.target`); }
      else if (a.type === "launchGame") { keys(a, ["type", "gameId"], ["type", "gameId"], `${p}.props.action`); uuid(a.gameId, `${p}.props.action.gameId`); if (!games.has(a.gameId)) fail("MISSING_GAME", "Launch action references an unknown game", `${p}.props.action.gameId`); }
      else fail("UNSUPPORTED_ACTION", "Only navigation and configured game launch are supported", `${p}.props.action.type`);
    } else if (node.type === "gameCard") {
      keys(node.props, ["gameId"], ["gameId"], `${p}.props`); uuid(node.props.gameId, `${p}.props.gameId`);
      if (!games.has(node.props.gameId)) fail("MISSING_GAME", "Game card references an unknown game", `${p}.props.gameId`);
    }
  }
  project.components.forEach((component, i) => visit(component, 1, `$.components[${i}]`));
  return true;
}

export function parseProjectText(text) {
  if (typeof text !== "string") fail("INVALID_PROJECT_TEXT", "Project input must be UTF-8 text");
  if (new TextEncoder().encode(text).byteLength > MAX_PROJECT_BYTES) fail("PROJECT_TOO_LARGE", `Project JSON exceeds ${MAX_PROJECT_BYTES} bytes`);
  let project; try { project = JSON.parse(text); } catch { fail("INVALID_JSON", "Project file is not valid JSON"); }
  validateProject(project); return project;
}
