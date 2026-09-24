# AI Dev Stream Deck

A local Windows control panel for installed AI coding harnesses, PowerShell account profiles, and an Elgato Stream Deck.

Choose a project, harness and profile, then give the agent an **English objective**. The human interface supports **French and English** independently of the agent protocol. No API key is required by the launcher; each harness uses its own existing account and permissions.

## Requirements

- Windows, Python 3.11+ with Tk, and PowerShell 7 for mission launches.
- At least one installed AI CLI. Git is optional for context snapshots.
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

For other PowerShell wrappers, add an explicit local registration to `%LOCALAPPDATA%\AI Dev\profiles.local.json`:

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

The base layout has **65 configured positions across five pages** (including Back buttons): home, Prompts, Editor, AI Web and Apps. Additional profile pages are generated from the workstation's detected harnesses and PowerShell commands. It includes Factory, sessions, project selection, all 14 editor shortcuts, all 14 English prompts, Cursor, VS Code, Orca, capture, CPU/RAM, files and guide. See the [complete button map](docs/BUTTONS.md). Agent prompt buttons always insert English text and do not press Enter. Editor shortcuts target the active application. A running session continues when you switch Stream Deck pages.

**CODEX / CLAUDE / AGY** open their detected profile subpages. **PROFILES** lists every detected harness, including additional tools such as Cursor. Each profile key (for example `CODEX / WORK`) opens the mission panel with that exact command selected, overriding any remembered account. It does not start a paid mission. Default CLI entries are explicitly labeled DEFAULT; unavailable CLI entries have an orange `!` marker. A removed or renamed profile produces an error instead of falling back to another account. Large inventories get MORE subpages; profile selection data stays outside the public source.

**REFRESH** on a profile page redetects the current PowerShell environment and opens the standard Stream Deck import dialog in that page's language. Install the generated profile to apply added/removed accounts to the hardware. Detection runs at generation and again when a profile is opened; imported physical labels are a snapshot, not a live watcher. Stream Deck may import an updated profile as a separate copy.

The panel language selector updates the interface immediately. **Update Stream Deck: profiles + language** detects profiles, generates an `AI Dev FR` or `AI Dev EN` profile and opens the standard Stream Deck import dialog. Install the generated profile there; once both languages are imported, use Stream Deck's profile selector to switch. Hardware labels are generated at import time, not live synchronized with the panel. Other Stream Deck sizes require a layout adapter; generating a profile does not edit installed profiles.

### Choose Chrome or Edge

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

Preferences, inventories you save, mission receipts, context snapshots, bridge dependencies and generated Stream Deck exports belong under `%LOCALAPPDATA%\AI Dev`, outside the checkout. Set `AI_DEV_DATA_DIR` to override this location. Do not set it inside a repository you publish.

Git snapshots contain metadata only: status, diff statistics and recent commit subjects. Each mission keeps its own snapshot. The app does not read source contents or authentication files. Snapshot metadata and your objectives may still be confidential; do not publish them.

A receipt records a prepared/running/exited/launch_error process state. **Activity & next actions** refreshes every four seconds and shows the selected session's objective, exit code and available error evidence. The panel stays open after launch. When a recorded runner no longer exists, the UI marks it interrupted without rewriting the original receipt. PID checks cannot prove objective completion and a reused PID can make an old receipt appear active. `exited` does not mean the objective succeeded. Costs and tokens remain unmeasured.

Completed or interrupted sessions offer **Prepare next mission**: an English verification or diagnosis objective, with the same project and exact profile when still available. A prepared receipt with no start confirmation after 30 seconds is shown as unconfirmed and offers diagnosis too. You review and launch it explicitly. This does not resume the original provider conversation or automatically retry a failed task.

## Factory integration

In **Factory control**, choose your existing `agentic-sdlc-factory` installation folder once (or set `AI_DEV_FACTORY`). Its path stays in private local settings. The **FACTORY** hardware button starts or reuses the native Factory workbench on loopback and opens it through the same Chrome/Edge chooser. The **CONTROL / PILOTAGE** button opens canonical task counts, executing attempts and pending decisions in AI Dev. Refresh reads `autopilot.py status --brief`; it never equates tasks marked executing with live agents.

The integration uses the Factory installation's virtual environment when present. It verifies the workbench's package identity, never takes over an unrelated service, and starts it with `127.0.0.1` binding. The workbench remains running after the panel closes. Logs are private under `factory/workbench.log`. Its native Git-health supervisor also runs as part of the existing workbench.

Factory's native workbench provides its task and execution controls. AI Dev displays budget/registration decisions and points you there; it does not invent a budget, bypass readiness, start autonomous runs, or create canonical tasks from ordinary CLI missions. The Factory installation target is independent of the mission project folder. The native workbench keeps its own last-selected project and language; check its project selector before acting. The AI Dev panel itself is bilingual, but this project does not translate Factory's separate interface.

## Tests and public export

```powershell
python -m unittest discover -s tests -v
python scripts/export_public.py ..\ai-dev-stream-deck-source.zip
```

The source exporter uses an allowlist and screens for common token formats and user-specific Windows paths. It exports no Git history, credentials, local profiles, generated device archives or mission data. Automated scanning is not proof that every possible secret format has been found; review the selected source files before publishing.

Public CI runs offline tests on Windows. It does not authenticate to providers, run paid AI tasks, or press physical hardware keys.

MIT licensed. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
