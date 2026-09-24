# AI Dev Stream Deck

A local Windows control panel for installed AI coding harnesses, PowerShell account profiles, and an Elgato Stream Deck.

No orchestrator is bundled, installed, cloned or required. Use the harnesses directly, connect an existing external Factory, or choose a custom orchestrator such as OpenClaw, AX or another tool via its executable or dashboard URL. Your selection stays in private local settings.

Choose a project, harness and profile, then give the agent an **English objective**. The human interface supports **French and English** independently of the agent protocol. No API key is required by the launcher; each harness uses its own existing account and permissions.

## Clean-install defaults

A fresh clone contains no user configuration. The first launch has no selected project, account, browser or orchestrator. Language follows Windows (French/English) until the user chooses otherwise. Configure only the tools you want; detected integrations are optional. Personal settings, account wrappers, credentials, device identities, missions and generated shortcuts remain outside the repository under the current user's private app-data folder. Existing users keep their own local preferences. See [first-run behavior](docs/FIRST-RUN.md).

## Requirements

- Windows, Python 3.11+ with Tk, and PowerShell 7 for mission launches.
- An installed AI CLI is needed to launch an AI session. The panel itself opens without one. Git is optional for context snapshots.
- Stream Deck software and a 15-key device for the supplied hardware layout. The desktop panel works without Stream Deck.
- Node.js 18+ and npm only if you enable the optional Elgato MCP bridge.

## Start

```powershell
git clone https://github.com/JacquesGariepy/ai-dev-stream-deck.git
cd ai-dev-stream-deck
python launch.py
```

There are no Python runtime dependencies beyond the standard library. Keep the checkout in its installed location; generated local shortcuts point to it. If Python or PowerShell is not on PATH, use its full path. `AI_DEV_POWERSHELL` can select a specific PowerShell executable, including the one whose startup profile defines your launchers.

## Detection

On opening the panel, AI Dev starts PowerShell **with the user's normal startup profile**, then inspects available commands. It does not sign in, start agents, or open credential files during discovery. PowerShell startup scripts themselves run normally, so use a profile you trust.

| Harness | Installed CLI discovery | Named profiles | Mission adapter |
|---|---|---|---|
| Codex | PATH and standard install location | PowerShell profile commands | Yes |
| Claude Code | PATH and standard install location | PowerShell profile commands | Yes |
| AGY | PATH and standard install location | PowerShell profile commands | Yes |
| Cursor CLI | `agent` / `cursor-agent`, standard CLI location | PowerShell profile commands | Interactive launch only |
| Gemini CLI, OpenCode, Aider, Copilot CLI | PATH | Registered PowerShell commands | Interactive launch only |

Named functions and aliases that call `Invoke-AiProfile -Tool 'name' -ProfileName 'name'` are detected automatically. Detection distinguishes an available CLI, a missing CLI, and a profile directory that has not been initialized. It does **not** prove authentication is valid. The Cursor desktop editor is not treated as Cursor CLI.

For other PowerShell wrappers, add an explicit local registration to `%LOCALAPPDATA%\AIDev\profiles.local.json`:

```json
[
  {"tool": "gemini", "profile": "work", "command": "gemini-work"}
]
```

The command must already exist in your loaded PowerShell profile. AI Dev rechecks the exact command before launch. It never evaluates command text from a profile name or objective. Arbitrary custom wrapper bodies are not interpreted to guess their account isolation.

## Language

The default UI follows the Windows **user locale** (for example `fr-CA` → French). Other languages fall back to English. The selector offers Auto, Français and English, and remembers your preference. This uses the user locale rather than the Windows display language; those settings can differ.

All app-authored agent instructions, workflow prompts and the requested agent response language are **English**, regardless of the UI language. You write the objective in English and confirm it before launching a mission. There is no translation service or automatic objective-language classifier; the checkbox records the user's confirmation, not machine validation. Code, paths and names are preserved literally. Interactive sessions opened without an objective remain under your direct control.

## Stream Deck

```powershell
pwsh -File scripts/Install.ps1 -StreamDeck
```

Import the `.streamDeckProfile` path printed by the installer. It is generated for **your workstation**, with local shortcut paths and the detected device. Never commit that generated archive. It is not a portable binary preset.

The first page is a general-purpose **Daily** desk: DEV, AGENTIC, detected applications, Windows tools, browser chooser, files, photo/video, media controls, clipboard history, Calculator, Notepad, CPU/RAM tools, desktop, settings and refresh. **Desktop / Bureau** opens display selection, monitor arrangement, virtual-desktop navigation, window movement between monitors and show/minimize/restore controls. Spotify is one detected application rather than a required dependency. Multimedia keys target the active Windows media session; no media account or plugin is bundled. Capture is omitted when Snipping Tool is unavailable.

**DEV** is workstation-first: it features up to four useful installed tools such as Docker Desktop, GitHub Desktop, Visual Studio Code, Cursor or Postman directly on the page. **DEV APPS** contains every detected development application. Terminal choice, editor shortcuts, Git, project selection, diagnostics, common debugging keys and real project tasks read from package, Python, Compose and Make manifests remain available. Opening the task list runs nothing; the user explicitly selects a task. **AGENTIC** groups missions, detected harness/account profiles, sessions, English prompts, local MCP declarations and the optional external orchestrator. When installed, Claude Desktop and ChatGPT Desktop receive direct keys with distinct original icons; **AI APPS** retains the complete detected AI application list. Each folder has a working Back key.

Up to three available harnesses, sorted by name, appear in AGENTIC. **PROFILES** lists every detected harness. Each profile key opens the mission panel with that exact command selected, without starting a paid mission. Removed selections never fall back to another account; unavailable CLI entries retain their orange `!` marker. Large profile, application and MCP inventories receive MORE subpages. Desktop-app keys preserve the exact Start-menu identity detected locally.

The MCP inventory reads known Codex, Claude Desktop, Claude Code, Cursor, VS Code, Windsurf, selected-project and user-added JSON/JSONC/TOML configuration files. It creates one inspection key per declaration without retaining command arguments, URLs, environment variables or headers. It does not start a server or claim that its connection and tools work.

Icons are generated from original code, packaged inside the local profile and require no downloaded icon pack or extra Python library. Labels follow the selected FR/EN language. Keyboard shortcuts target the active application; English prompt buttons insert text without pressing Enter. See the [complete button map](docs/BUTTONS.md).

Generation audits every key before import: all pages must be reachable, native folders must have one parent, action identifiers must be unique, icons must be valid PNG files and every Open key must point to a generated local shortcut. The audit does not execute applications, lock Windows, switch displays or run project tasks.

## Choose an installed Chrome, Edge, Firefox or Brave browser

Web buttons use AI Dev's browser launcher instead of the Windows default browser. **Ask before each opening** is enabled by default: choose Chrome or Edge for the active work/personal context, then save and open. No work/browser association is imposed.

Open **Web browsers** in the desktop panel or **BROWSER** in the Stream Deck AI Web folder to change preferences. Disable the ask option to open links directly with the saved browser. **WORK** and **PERSONAL** select the web context; they do not change any CLI account profile. If the chosen browser is missing, AI Dev asks again instead of silently using another browser.

The app uses the selected browser's existing session. It does not sign in, move cookies or select a particular internal Chrome/Edge profile. Browser choices are stored only in local settings. Regenerate/reimport an older exported Stream Deck profile to replace its native default-browser website actions.

## Optional Elgato MCP

```powershell
pwsh -File scripts/Install.ps1 -ElgatoMcp
```

This installs the pinned official `@elgato/mcp-server@0.1.7` bridge under private app data and configures it for new Codex and Claude sessions launched here. It does not modify existing sessions or global harness settings. Enable **MCP Deck** in Stream Deck, copy the actions you want to expose into that virtual deck, and supply English AI descriptions. Physical profile actions are not automatically exposed by Stream Deck.

The bridge is not bundled or implemented by this project. AGY and other harnesses keep their existing MCP configuration; no automatic MCP setup is claimed for them.

## Runtime state and limits

Preferences, inventories you save, mission receipts, context snapshots, bridge dependencies and generated Stream Deck exports belong under **`%LOCALAPPDATA%\AIDev`**, outside the checkout. The app-created directory name has no spaces. Set `AI_DEV_DATA_DIR` to override this location. Do not set it inside a repository you publish. Paths containing spaces are still accepted and correctly quoted when selected by the user.

On upgrade, the launcher copies legacy `%LOCALAPPDATA%\AI Dev` data into `AIDev` once, preserving existing destination files and retaining the old directory as a backup. Runtime references in copied settings/receipts are updated; objectives are preserved literally. Generated shortcuts and deck archives are rebuilt for the new path. Run `python scripts/migrate_data.py` to perform the migration explicitly. Import a newly generated deck profile after migration; old imported profiles still reference their old shortcuts. Existing running processes are not restarted.

## Engineering diagnostics and session evidence

**Sessions** opens without running PowerShell discovery, so unavailable harnesses or startup-profile failures cannot block access to recorded sessions. Unreadable directories and corrupt receipts produce an inline warning; readable sessions remain available. Startup and UI callback errors are visible and logged privately to `AIDev/logs/aidev.log` (one previous file is retained after rotation). If that folder is itself inaccessible, the error is displayed without claiming a log was saved.

Select a session to open its JSON receipt or Git snapshot as text, or copy an **English handoff** containing its objective, exact profile, observed state and evidence paths. Copying does not send data to an AI. Missing artifacts produce an explicit error. These are AI Dev-launched session receipts, not an inventory of every conversation in every provider.

The **Diagnostics** tab and **HEALTH / DIAG**, **GIT**, **LOGS / JOURNAUX** keys expose real tool/profile availability, data-directory write access, presence of configured MCP bridge files, local Git branch/changes/worktrees and private application logs. Checks run in background workers. Git inspection performs no fetch or mutation. Tool detection does not read credentials or prove sign-in; MCP file presence is not a connectivity test. Physical key labels remain static after import; current results appear in the panel. See [engineering priorities](docs/ENGINEERING.md) for proposed additions and their evidence requirements.

Git snapshots contain metadata only: status, diff statistics and recent commit subjects. Each mission keeps its own snapshot. The app does not read source contents or authentication files. Snapshot metadata and your objectives may still be confidential; do not publish them.

A receipt records a prepared/running/exited/launch_error process state. **Activity & next actions** refreshes every four seconds and shows the selected session's objective, exit code and available error evidence. The panel stays open after launch. When a recorded runner no longer exists, the UI marks it interrupted without rewriting the original receipt. PID checks cannot prove objective completion and a reused PID can make an old receipt appear active. `exited` does not mean the objective succeeded. Costs and tokens remain unmeasured.

Completed or interrupted sessions offer **Prepare next mission**: an English verification or diagnosis objective, with the same project and exact profile when still available. A prepared receipt with no start confirmation after 30 seconds is shown as unconfirmed and offers diagnosis too. You review and launch it explicitly. This does not resume the original provider conversation or automatically retry a failed task.

When several compatible Stream Deck devices are configured, generation requires an explicit selection: `python scripts/stream_deck.py --device-id "<device-id-shown-by-the-tool>"`. That choice is saved only locally. The supplied layout currently supports the 15-key `20GBA9901` model; unsupported models are reported clearly and the desktop app remains usable. Generated device archives must not be published.

## Optional external orchestrators

In **Orchestrator (optional)**, **Choose orchestrator / Factory** offers **None**, **Factory (external)** and **Custom**. New installations default to None. Existing explicit Factory settings are preserved; choosing None overrides them without deleting the saved installation path. Project folders never implicitly select Factory.

For a custom orchestrator, enter its name and either its dashboard URL or its executable, argument list and working directory. For scripts, select the interpreter executable and pass the script path as an argument. The app does not guess provider-specific commands, install dependencies or launch anything when saving. OpenClaw and AX are examples of user-selected tools, not claims of dedicated adapters. Generic integrations expose no task, token, cost or agent telemetry; use the orchestrator's own interface.

The **ORCH** key opens the selected external tool; **CONTROL / PILOTAGE** opens its configuration and supported status. Existing Factory shortcut names remain compatible and route through this selection. Reimport the generated Stream Deck profile to update its visible label.

### Optional Factory adapter

Choose your existing `agentic-sdlc-factory` installation folder (or use the legacy `AI_DEV_FACTORY` setting). The repository contains only the optional adapter, not Factory source, tasks or dependencies. Its path stays in private local settings. When Factory is selected, **ORCH** starts or reuses its workbench on loopback and opens it through the browser chooser. **CONTROL / PILOTAGE** shows canonical task counts and pending decisions. Refresh reads `autopilot.py status --brief`; it never equates tasks marked executing with live agents.

The integration uses the Factory installation's virtual environment when present. It verifies the workbench's package identity, never takes over an unrelated service, and starts it with `127.0.0.1` binding. The workbench remains running after the panel closes. Logs are private under `factory/workbench.log`. Its native Git-health supervisor also runs as part of the existing workbench.

Factory's native workbench provides its task and execution controls. AI Dev displays budget/registration decisions and points you there; it does not invent a budget, bypass readiness, start autonomous runs, or create canonical tasks from ordinary CLI missions. The Factory installation target is independent of the mission project folder. The native workbench keeps its own last-selected project and language; check its project selector before acting. The AI Dev panel itself is bilingual, but this project does not translate Factory's separate interface.

## Terminal chooser

The Stream Deck **TERMINAL** button opens a bilingual chooser on every press. It discovers CMD, Windows PowerShell, PowerShell 7 installations, Git Bash, Windows Terminal, installed WSL distributions and common optional terminal applications. Discovery runs in the background without executing PowerShell profiles or starting WSL distributions. PowerShell profiles load when you actually open PowerShell.

The selected project is the starting folder for supported shells. Generic terminal applications may override it with their own startup settings. The last choice is preselected; **Refresh** scans again, and **Add another executable** covers portable or custom installations outside known locations. Choices and executable paths remain private under `AIDev`; nothing is uploaded. Existing TERMINAL shortcuts use the chooser without reimporting the Stream Deck profile.

## System details and screen capture

On Stream Deck's **APPS** page, **CPU / RAM** opens a folder with Task Manager, Resource Monitor (per-process CPU, memory, disk and network), Performance Monitor and System Information. These open existing Windows tools; no background collector or fabricated statistics are used.

**PHOTO / VIDEO** opens Windows Snipping Tool, where you choose a screenshot or video recording. You choose the region and start recording yourself; the button does not start a recording. Video recording requires a compatible Snipping Tool version on Windows 11. The existing **CAPTURE** key still opens the screenshot overlay directly. Import the regenerated profile to install these new keys.

## Tests and public export

```powershell
python -m unittest discover -s tests -v
python scripts/export_public.py ..\ai-dev-stream-deck-source.zip
```

The source exporter uses an allowlist and screens for common token formats and user-specific Windows paths. It exports no Git history, credentials, local profiles, generated device archives or mission data. Automated scanning is not proof that every possible secret format has been found; review the selected source files before publishing.

Public CI runs offline tests on Windows. It does not authenticate to providers, run paid AI tasks, or press physical hardware keys.

MIT licensed. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
