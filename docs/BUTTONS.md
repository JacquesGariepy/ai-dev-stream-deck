# Expert Stream Deck button map

The deck is generated from a declarative layout (`aidev/deck_layout.py`) for the detected device: Mini (3×2), Neo / + (4×2), original and MK.2 (5×3) and XL (8×4). Only the MK.2 layout is verified on hardware; any other grid can be forced with `--grid COLSxROWS`. All icons are original, bundled PNGs with FR/EN labels. No personal account or device identity is distributed.

## Ergonomic rules

- **Fixed positions.** On every subpage, **BACK** is the top-left key. When a page overflows, **MORE** is always the bottom-right key and the next page starts with BACK again.
- **Stable cockpit.** The home layout never shifts: if fewer than three harnesses are detected, their slots keep PROFILES, CONTEXT and AI WEB instead of moving the other keys.
- **Colour zones.** Violet = agentic, teal = dev, orange = Git, yellow = build/test/debug, blue = system, green = media, cyan = web, grey = navigation, red = unavailable or disruptive (for example Lock, Close desktop). Unavailable harness profiles keep the orange `!` title.
- **One parent per folder.** A folder reachable from several places (for example GIT from home and DEV) is generated as separate native copies, which Stream Deck requires. The audit rejects shared parents, unreachable pages, keys outside the grid, subpages without BACK and missing shortcuts or icons.

## Home (15 keys)

| Row | Keys |
|---|---|
| 1 — agentic | MISSION · harness 1 · harness 2 · harness 3 · SESSIONS |
| 2 — dev | TERMINAL · EDITOR · GIT · BUILD/TEST · PROMPTS |
| 3 — folders | AGENTIC · DEV · SYSTEM · MEDIA · REFRESH |

A harness with exactly one detected profile opens that exact profile in one press; a harness with several profiles opens its profile folder. **XL** adds the six mission workflows, direct BUILD/TEST/LINT and STATUS/PULL/COMMIT/PUSH on the home page. **Mini, Neo and +** keep the same priority order (MISSION, harness, TERMINAL, GIT, SESSIONS, BUILD/TEST…) and continue on MORE pages.

## Pages

| Page | Controls |
|---|---|
| AGENTIC | Back; mission workflows PLAN, IMPLEMENT, REVIEW, DEBUG, TEST, HANDOFF (panel opens with the workflow preselected); Sessions, Context, Profiles, Prompts, AI Web, MCP, AI Apps, Orchestrator |
| GIT | Back; Status, Diff, Log, Fetch, Add -p, Commit, Pull (fast-forward only), Push (confirmed), New branch (name validated by Git), Switch (local branch list), Stash, Stash pop, Git panel (read-only), Git Web |
| BUILD / TEST | Back; Build, Test, Lint, Dev server, Types, Format (each runs the matching project script), All tasks, Debug folder, Terminal |
| DEV | Back; Terminal, Editor, Build/Test, Debug, Git, Project, Files, Diagnostics, Logs, Dev Apps, then up to four of: Cursor / VS Code (open the project), Docker Desktop, GitHub Desktop, Postman… |
| Editor | Back; Commands, Find file, Search, Save, Format, Copy, Paste, Panel, Problems, Rename, Definition, Undo, Redo, Escape |
| Debug | Back; Start F5, Stop, Restart, Breakpoint, Step over/into/out, Build |
| Prompts | Back; Implement, Plan, Debug, Review, Tests, Handoff, Refactor, Explain, Performance, Security, Docs, Context, Usage/costs, PR draft (English text, never submitted) |
| SYSTEM | Back; Apps, Windows, Desktop, CPU/RAM, Browser, Files, Photo/Video (when Snipping Tool exists), Clipboard, Calculator, Notepad, Search, Lock, Windows Settings, AI Dev |
| AI Dev | Back; Settings (language, deck update), Diagnostics, Logs, Guide, Refresh |
| Media | Back; Previous, Play/Pause, Next, Mute, Volume −/+, Spotify when installed |
| Windows | Back; Display, Sound, Network, Bluetooth, Storage, Downloads, Documents, Pictures, Recycle Bin, Emoji, Task view, Services, Event Viewer |
| Desktop | Back; Show desktop, Task view, Display mode, Display settings, Snip, new/previous/next/close virtual desktop, move window left/right monitor, minimize, restore |
| CPU / RAM | Back; Task Manager, Resource Monitor, Performance Monitor, System Information (only installed tools) |
| AI Web | Back; Browser settings, Work, Personal, ChatGPT, Claude, Gemini, Perplexity, GitHub, Pull requests, Issues |
| Profiles | Back; Mission, Refresh, each detected harness (MORE when needed) |
| Each harness | Back; Panel, Refresh, each exact profile/default CLI (MORE when needed) |
| Apps / Dev Apps / AI Apps | Back; searchable panel, Refresh, exact Start-menu applications (Claude and ChatGPT Desktop first in AI Apps) |
| MCP | Back; MCP inventory, Refresh, each sanitized local MCP declaration |
| Orchestrator | Back; ORCH, Control |

## What the expert keys do

- **Mission workflows** open the panel with the workflow, last project and remembered profile preselected. Nothing starts until you press Launch; the English-objective confirmation still applies.
- **Git keys** run one fixed `git` command in a new visible terminal in the selected project: `status --short --branch`, `diff`, `log --graph -n 40`, `fetch --all --prune`, `pull --ff-only`, `add --patch`, `commit --verbose`, `stash push --include-untracked`, `stash pop`. **Push** first shows branch, destination and commits ahead; without an upstream it proposes `push --set-upstream origin HEAD` only when `origin` exists. **New branch** validates the name with `git check-ref-format --branch`. Nothing is evaluated by a shell and no command force-pushes, resets or deletes.
- **Build/Test keys** pick the project's own script (`package.json`, pytest/unittest, `Makefile`): exact names first (`test`), then prefixed ones (`test:unit`). When nothing matches, the task list opens instead so nothing unexpected runs. Scripts come from your project and may modify files or use the network.

## Editor shortcuts

| Control | Windows shortcut |
|---|---|
| Commands | Ctrl+Shift+P |
| Find file | Ctrl+P |
| Search | Ctrl+Shift+F |
| Save | Ctrl+S |
| Format | Alt+Shift+F |
| Copy / Paste | Ctrl+C / Ctrl+V |
| Panel | Ctrl+J |
| Problems | Ctrl+Shift+M |
| Rename / Definition | F2 / F12 |
| Undo / Redo | Ctrl+Z / Ctrl+Y |
| Escape | Escape |
| Debug start / stop / restart | F5 / Shift+F5 / Ctrl+Shift+F5 |
| Snip (Desktop page) | Win+Shift+S |

These target the focused app and use common VS Code/Cursor defaults; custom keybindings can change the effect. Media keys use [Windows virtual-key codes](https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes) with [Qt key identifiers](https://doc.qt.io/qt-6.8/qt.html) and control the active media session.

## Language, profiles and agent control

- **Profiles** lists every detected harness, including unavailable wrappers marked `!`. A profile key opens the panel with its exact command selected, overriding the remembered account; stale keys refuse to select another account.
- **Refresh / Actualiser** redetects harnesses, profiles, apps and MCP declarations, regenerates the deck for the same device and opens the standard import. Physical keys are not live status badges.
- **Sessions** opens live receipt observations and the suggested verification/diagnosis mission.
- **Settings** (AI Dev page) opens the panel language selector; both imported languages can coexist.
- Web context keys do not switch a CLI account or a browser's internal profile. Subpages never stop running agents.
