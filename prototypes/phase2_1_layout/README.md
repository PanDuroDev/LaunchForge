# Phase 2.1 Layout Reference Prototype

This is an isolated, dependency-free Python reference prototype for LaunchForge Phase 2.1. It is **not** the production editor, renderer, project schema, or Runtime. Python is used only to make proposed geometry rules executable while the Phase 0/1 stack and shared contracts remain unapproved.

## Included behavior

- Horizontal and vertical stacks.
- Fixed, fit-content, and weighted fill sizing.
- Minimum/maximum constraints with weighted redistribution.
- Padding, gaps, start/center/end/space-between distribution.
- Cross-axis start/center/end/stretch alignment.
- Logical horizontal ordering for RTL.
- Overlay placement with directional edge alignment.
- Explicit overflow reporting and input validation.
- Logical UI units only. DPI conversion is deliberately left to the renderer boundary.

## Run tests

From this directory:

```sh
python -m unittest discover -s tests -v
python -m compileall -q launchforge_layout tests
```

No third-party packages are required.

## Contract boundary

The module accepts typed in-memory inputs and returns logical rectangles. It does not serialize project nodes, select a renderer, define component IDs, persist assets, or call Studio/Runtime APIs. Its types and allocation rules are proposal-level behavior and must be compared with the accepted Phase 0/1 renderer and schema contracts before production integration. Do not copy these Python types into the project schema as-is.

The current proposed fill rule distributes remaining main-axis space by weight after fixed/fit children and base gaps are accounted for. When a fill child's min/max constraint is reached, that child is frozen at the bound and the remaining space is redistributed. If minimum constraints exceed available space, the minimums are preserved and overflow is reported.

See [Issue #4](https://github.com/PanDuroDev/LaunchForge/issues/4) and the [Phase 2 authoring specification PR](https://github.com/PanDuroDev/LaunchForge/pull/10).
