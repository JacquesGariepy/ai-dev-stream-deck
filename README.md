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

The profile includes Mission, Codex, Claude, AGY, profiles, project selection, Git context, sessions, terminal, files and guide, plus **Prompts**, **Editor**, and **AI Web** subpages. Agent prompt buttons always insert English text and do not press Enter. Editor shortcuts target the active application. A running session continues when you switch Stream Deck pages.

Regenerate/reimport to change the physical button language. Changing the panel language updates the panel immediately. Other Stream Deck sizes require a layout adapter; existing profiles are not overwritten by generation.

## Optional Elgato MCP

```powershell
pwsh -File scripts/Install.ps1 -ElgatoMcp
```

This installs the pinned official `@elgato/mcp-server@0.1.7` bridge under private app data and configures it for new Codex and Claude sessions launched here. It does not modify existing sessions or global harness settings. Enable **MCP Deck** in Stream Deck, copy the actions you want to expose into that virtual deck, and supply English AI descriptions. Physical profile actions are not automatically exposed by Stream Deck.

The bridge is not bundled or implemented by this project. AGY and other harnesses keep their existing MCP configuration; no automatic MCP setup is claimed for them.

## Runtime state and limits

Preferences, inventories you save, mission receipts, context snapshots, bridge dependencies and generated Stream Deck exports belong under `%LOCALAPPDATA%\AI Dev`, outside the checkout. Set `AI_DEV_DATA_DIR` to override this location. Do not set it inside a repository you publish.

Git snapshots contain metadata only: status, diff statistics and recent commit subjects. Each mission keeps its own snapshot. The app does not read source contents or authentication files. Snapshot metadata and your objectives may still be confidential; do not publish them.

A receipt records a prepared/running/exited/launch_error process state. `exited` does not mean the objective succeeded. Closing a terminal forcibly can leave a stale `running` receipt. Costs and tokens remain null unless a future measured integration supplies them. This is an interactive launcher, not a background swarm or autonomous scheduler.

Factory/tk integration is **not implemented** in this release. Launching from here does not create or complete a canonical Factory task.

## Tests and public export

```powershell
python -m unittest discover -s tests -v
python scripts/export_public.py ..\ai-dev-stream-deck-source.zip
```

The source exporter uses an allowlist and screens for common token formats and user-specific Windows paths. It exports no Git history, credentials, local profiles, generated device archives or mission data. Automated scanning is not proof that every possible secret format has been found; review the selected source files before publishing.

Public CI runs offline tests on Windows. It does not authenticate to providers, run paid AI tasks, or press physical hardware keys.

MIT licensed. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
