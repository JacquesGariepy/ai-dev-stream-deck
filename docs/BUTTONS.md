# Complete Stream Deck button map

The 15-key layout has 65 configured positions: 15 home, 15 prompts, 15 editor, 11 web, 9 apps. Each subpage has a Back button. All hardware names follow the generated FR/EN language. Agent prompt contents and MCP action descriptions remain English.

| Page | Controls |
|---|---|
| Home | Mission, Codex, Claude, AGY, Profiles, Factory, Git context, Sessions, Editor folder, AI Web folder, Prompts folder, Terminal, Apps folder, Project, Factory control |
| Prompts | Back; Implement, Plan, Debug, Review, Tests, Handoff, Refactor, Explain, Performance, Security, Docs, Context, Usage/costs, PR draft |
| Editor | Back; Commands, Find file, Search, Save, Format, Copy, Paste, Panel, Problems, Rename, Definition, Undo, Redo, Escape |
| AI Web | Back; Browser settings, Work, Personal, ChatGPT, Claude, Gemini, Perplexity, GitHub, Pull requests, Issues |
| Apps | Back; Cursor desktop, VS Code, Orca, CPU/RAM, Capture, Files, Guide, Settings/language |

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

- **Profiles / Mission** detects installed harnesses and PowerShell account commands; choose the exact profile before launch.
- **Sessions** opens live receipt observations and the next suggested verification/diagnosis mission.
- **Factory** opens the native local workbench through your chosen Chrome/Edge context. **Control** reads Factory status and blockers.
- **Settings** opens the panel language selector. Choose Français or English, then Apply language to Stream Deck and install the generated profile. Both imported languages can coexist.
- Web context controls do not switch a CLI account or a browser's internal profile.
- Subpages do not stop running agents. MCP exposure remains a separate virtual deck managed in Stream Deck.
