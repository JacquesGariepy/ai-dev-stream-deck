# Complete Stream Deck button map

The 15-key layout starts with a general-purpose Daily page and two work folders. Counts depend on installed tools; every subpage has Back. All icons are original, bundled PNGs with FR/EN labels. No personal account or device identity is distributed.

| Page | Controls |
|---|---|
| Daily / Home | DEV, AGENTIC, Browser, Files, Spotify, Previous, Play/Pause, Next, Mute, Photo/Video, Volume down/up, Desktop, CPU/RAM, Windows Settings |
| DEV | Back, Terminal chooser, Editor, Apps, Git, Project, Files, Diagnostics, Logs |
| AGENTIC | Back, Mission, up to three detected harnesses, Profiles, optional Orchestrator, Context, Sessions, AI Web, Prompts, Control |
| Prompts | Back; Implement, Plan, Debug, Review, Tests, Handoff, Refactor, Explain, Performance, Security, Docs, Context, Usage/costs, PR draft |
| Editor | Back; Commands, Find file, Search, Save, Format, Copy, Paste, Panel, Problems, Rename, Definition, Undo, Redo, Escape |
| AI Web | Back; Browser settings, Work, Personal, ChatGPT, Claude, Gemini, Perplexity, GitHub, Pull requests, Issues |
| Apps | Back; detected desktop apps, CPU/RAM, Capture, Files, Guide, AI Dev settings, Diagnostics, Git, Logs, Photo/Video |
| CPU/RAM | Back; Task Manager, Resource Monitor, Performance Monitor, System Information |
| Profiles | Back; Mission, Refresh, each detected harness, More when needed |
| Each harness | Back; Panel, Refresh, each exact detected profile/default CLI, More when needed |

Spotify opens locally when detected, otherwise it offers its web player using the browser chooser. Playback and volume use [Windows media keys](https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes), with [Qt key identifiers](https://doc.qt.io/qt-6.8/qt.html). They control the active media player; they do not guarantee exclusive Spotify control, display album art, authenticate an account or start playback when generating/importing a profile.

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
| Capture (Apps page) | Win+Shift+S |

These target the currently focused app and use common VS Code/Cursor defaults; custom keybindings can change the effect. Text prompts insert English without submitting. CPU/RAM opens the system-tools folder; it is not a streaming metric on the key. Desktop-tool keys are generated only for detected installations. A tool removed after generation produces an error rather than launching another app.

## Language, profiles and agent control

- **Detected harnesses** open their profile folders. AGENTIC features up to three available tools in alphabetical order. **Profiles** lists all detected harnesses, including unavailable wrappers marked `!`. A profile key opens the panel with its exact command selected, overriding the remembered account. No agent starts until you choose Open session or Launch mission.
- **Refresh / Actualiser** redetects profiles and opens the standard profile import. Install the generated profile to update hardware labels. Detection is not a live hardware watcher; stale profile keys refuse to silently select another account.
- **Sessions** opens live receipt observations and the next suggested verification/diagnosis mission.
- **Health / Diag** checks installed tools and storage access. **Git** inspects the currently selected project. **Logs / Journaux** opens private error logs. Results are refreshed in AI Dev; physical labels are not live status badges.
- **ORCH** opens the selected external orchestrator or offers configuration. Choose None, external Factory, or a custom executable/URL. **Control** reads Factory status only when its optional adapter is selected; other tools have no implied telemetry integration.
- **Settings** opens the panel language selector. Choose Français or English, then Update Stream Deck: profiles + language and install the generated profile. Both imported languages can coexist.
- Web context controls do not switch a CLI account or a browser's internal profile.
- Subpages do not stop running agents. MCP exposure remains a separate virtual deck managed in Stream Deck.
