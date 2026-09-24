# Complete Stream Deck button map

The 15-key layout has 74 base positions: 15 home, 15 prompts, 15 editor, 11 web, 13 apps, 5 system, plus generated harness/profile pages. Each subpage has a Back button. All hardware names follow the generated FR/EN language; account names retain their actual names. Agent prompt contents and MCP action descriptions remain English.

| Page | Controls |
|---|---|
| Home | Mission, Codex, Claude, AGY, Profiles, ORCH (optional external orchestrator), Git context, Sessions, Editor folder, AI Web folder, Prompts folder, Terminal chooser, Apps folder, Project, Orchestrator control |
| Prompts | Back; Implement, Plan, Debug, Review, Tests, Handoff, Refactor, Explain, Performance, Security, Docs, Context, Usage/costs, PR draft |
| Editor | Back; Commands, Find file, Search, Save, Format, Copy, Paste, Panel, Problems, Rename, Definition, Undo, Redo, Escape |
| AI Web | Back; Browser settings, Work, Personal, ChatGPT, Claude, Gemini, Perplexity, GitHub, Pull requests, Issues |
| Apps | Back; Cursor desktop, VS Code, Orca, CPU/RAM folder, Capture, Files, Guide, Settings/language, Health/Diag, Git, Logs/Journaux, Photo/Video |
| CPU/RAM | Back; Task Manager, Resource Monitor, Performance Monitor, System Information |
| Profiles | Back; Mission, Refresh, each detected harness, More when needed |
| Each harness | Back; Panel, Refresh, each exact detected profile/default CLI, More when needed |

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

These target the currently focused app and use common VS Code/Cursor defaults; custom keybindings can change the effect. Text prompts insert English without submitting. CPU/RAM opens Task Manager; it is not a streaming metric on the key. Desktop tools must be installed in a supported Windows location; missing tools produce an error instead of launching a different app.

## Language, profiles and agent control

- **Codex / Claude / AGY** open their profile folders when detected. **Profiles** lists all detected harnesses, including unavailable wrappers marked `!`. A profile key opens the panel with its exact command selected, overriding the remembered account. No agent starts until you choose Open session or Launch mission.
- **Refresh / Actualiser** redetects profiles and opens the standard profile import. Install the generated profile to update hardware labels. Detection is not a live hardware watcher; stale profile keys refuse to silently select another account.
- **Sessions** opens live receipt observations and the next suggested verification/diagnosis mission.
- **Health / Diag** checks installed tools and storage access. **Git** inspects the currently selected project. **Logs / Journaux** opens private error logs. Results are refreshed in AI Dev; physical labels are not live status badges.
- **ORCH** opens the selected external orchestrator or offers configuration. Choose None, external Factory, or a custom executable/URL. **Control** reads Factory status only when its optional adapter is selected; other tools have no implied telemetry integration.
- **Settings** opens the panel language selector. Choose Français or English, then Update Stream Deck: profiles + language and install the generated profile. Both imported languages can coexist.
- Web context controls do not switch a CLI account or a browser's internal profile.
- Subpages do not stop running agents. MCP exposure remains a separate virtual deck managed in Stream Deck.
