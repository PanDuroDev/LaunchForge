import { validateProject } from "./contract.mjs";

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function resolveText(value, gamesById) {
  if (typeof value === "string") return value;
  const game = gamesById.get(value.gameId);
  return game[value.field];
}

function renderNode(node, context) {
  const { gamesById, assetsById, theme } = context;
  const id = escapeHtml(node.id);
  const props = node.props;

  switch (node.type) {
    case "container": {
      const children = node.children.map((child) => renderNode(child, context)).join("");
      return `<section class="lf-container lf-container--${props.axis}" data-component-id="${id}" style="gap:${props.gap}px;padding:${props.padding}px;background-color:${theme[props.background]}">${children}</section>`;
    }
    case "text": {
      const value = escapeHtml(resolveText(props.value, gamesById));
      return `<p class="lf-text" data-component-id="${id}" style="font-size:${props.fontSize}px;color:${theme[props.color]}">${value}</p>`;
    }
    case "image": {
      const asset = assetsById.get(props.assetId);
      return `<img class="lf-image" data-component-id="${id}" src="./${escapeHtml(asset.path)}" alt="${escapeHtml(props.alt)}" style="object-fit:${props.fit}" loading="eager">`;
    }
    case "button": {
      const actionAttributes = props.action.type === "navigate"
        ? `data-lf-action="navigate" data-lf-target="${escapeHtml(props.action.target)}"`
        : `data-lf-action="launchGame" data-lf-game-id="${escapeHtml(props.action.gameId)}"`;
      return `<button class="lf-button" data-component-id="${id}" ${actionAttributes} type="button">${escapeHtml(props.label)}</button>`;
    }
    case "gameCard": {
      const game = gamesById.get(props.gameId);
      const asset = assetsById.get(game.coverAssetId);
      return `<article class="lf-game-card" data-component-id="${id}"><img class="lf-game-card__cover" src="./${escapeHtml(asset.path)}" alt="${escapeHtml(game.title)} cover"><div class="lf-game-card__copy"><h2>${escapeHtml(game.title)}</h2><p>${escapeHtml(game.description)}</p></div></article>`;
    }
    default:
      throw new Error(`Unsupported component type reached renderer: ${node.type}`);
  }
}

export function renderProjectMarkup(project) {
  validateProject(project);
  const context = {
    gamesById: new Map(project.games.map((game) => [game.id, game])),
    assetsById: new Map(project.assets.map((asset) => [asset.id, asset])),
    theme: project.theme,
  };
  return project.components.map((component) => renderNode(component, context)).join("");
}

export function mountProject(root, project, onAction = () => {}) {
  if (!root || typeof root.addEventListener !== "function") throw new TypeError("A DOM root element is required");
  root.innerHTML = renderProjectMarkup(project);
  const onClick = (event) => {
    const button = event.target?.closest?.("[data-lf-action]");
    if (!button || !root.contains(button)) return;
    if (button.dataset.lfAction === "navigate") onAction({ type: "navigate", target: button.dataset.lfTarget });
    else if (button.dataset.lfAction === "launchGame") onAction({ type: "launchGame", gameId: button.dataset.lfGameId });
  };
  root.addEventListener("click", onClick);
  return () => root.removeEventListener("click", onClick);
}
