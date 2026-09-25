# The developer control panel

Choose **AI Dev Agentic** in Stream Deck. The name stays stable across updates.

## Home

| DEV | AI / IA | DAILY / QUOTIDIEN | MEDIA | SEARCH / RECHERCHE |
|---|---|---|---|---|
| Terminals | Power User | Git | Installed apps | Screenshot / video |
| Clipboard history | Dictation | Desktops / screens | Choose project | Settings |

Keys use native Stream Deck actions for shortcuts, or a small local PowerShell dispatcher for tools that need context. The Classic Python control panel is not opened by these keys.

## What each area does

**DEV:** detected build, test, lint, development server, types and format tasks; Git; editor and debugger shortcuts; terminals; local documentation links. Installed Orca, editors, Docker Desktop and other developer apps receive direct launch keys.

**AI:** Claude Desktop, ChatGPT Desktop and Orca when installed, web services, CLI sessions, account profiles and task workflows. Orca has a direct launch key on both DEV and AI. Desktop applications keep their own signed-in account. CLI work/personal selection does not change a desktop application's account.

**DAILY:** Calculator, Notepad, files, Run, Windows Search, lock, clipboard operations, display, sound, network, Bluetooth, storage, standard folders, services and events. Task Manager, Resource Monitor, Performance Monitor and System Information show real Windows diagnostics.

**MEDIA:** previous, play/pause, next, mute and volume; installed media apps; YouTube; screenshot and video capture. Opening capture does not start a recording.

**SEARCH:** Google, Bing, DuckDuckGo, GitHub code search, Stack Overflow, YouTube and Perplexity. The query dialog can preload the clipboard. Review the query and choose a browser before sending it. Saved browser choices are independent for each account profile.

**APPS:** every discovered Start-menu application, grouped into short alphabetic sections. This is an inventory, not a recommendation to run every item. Re-scan after installing or removing tools.

## Power User diagnostics

These keys run a specific diagnostic in an interactive terminal. Read the output there, then copy a relevant excerpt into AI → Fix or Search if you need help interpreting it.

| Key | Useful when | What runs |
|---|---|---|
| TCP ports | A development server says its port is occupied | Listening TCP connections with owner process and PID |
| Processes | You need to identify the parent of a process | Process names, process IDs and parent IDs |
| Test connection | A local service, remote host or development port is unreachable | `Test-NetConnection` for the host and port you enter |
| DNS | A domain resolves incorrectly or cannot be found | `Resolve-DnsName` for the host you enter |
| IP / routes | You need to check interface, gateway or DNS configuration | IP configuration, routes and DNS servers |
| PATH | A command is missing or the wrong installation takes precedence | PATH entries in order, missing directories and duplicates |
| Disk | A build or container fails because storage is full | Volume capacity and free space |
| Startup | Too many applications start with Windows | Startup program names and locations |
| WSL | A Linux development environment will not start | `wsl --status` and distribution listing |
| Docker | You need container status and resource usage | `docker ps -a` and `docker stats --no-stream` |
| Long paths | Windows or Git reports a path-length failure | Windows long-path setting and `git core.longpaths` |

Diagnostics do not require selecting a project. The selected project, when available, supplies Git context for Long paths. Commands report missing prerequisites or insufficient access instead of treating an empty output as a successful check. No process is killed and no system setting is changed.

## Git in the active terminal

Git keys use the active PowerShell prompt and its current working directory. They never start a new terminal or use the project's saved location. Focus the terminal you want, leave its input line empty, then press STATUS, DIFF or another Git key. A nonempty input line is preserved and the key is ignored.

Install with `python scripts/agent_deck.py --install --enable-shell`, or choose **Settings → Terminal setup**. New PowerShell sessions load the integration automatically. For an existing session, run `Import-Module AIDevTerminal` once. This works in PowerShell 5.1 and 7, including supported terminal hosts; CMD, Bash and remote shells need their own integration.

The native bindings are Ctrl + Alt + F13 through F23, in order: status, diff, log, fetch, pull, push, stage, switch, branch, stash, apply stash. Existing custom bindings are preserved. Git's prompts and results stay in the same terminal. The module's `Invoke-AIDevGit` command also works directly from that prompt.

## Useful Windows keys

| Action | Windows shortcut |
|---|---|
| Clipboard history | Win + V |
| Voice dictation | Win + H |
| Screenshot selection | Win + Shift + S |
| Arrange windows | Win + Z |
| Screen projection mode | Win + P |
| Move window between monitors | Win + Shift + Left / Right |
| Switch virtual desktop | Win + Ctrl + Left / Right |
| New virtual desktop | Win + Ctrl + D |
| Quick settings | Win + A |
| Notifications | Win + N |
| Task Manager | Ctrl + Shift + Esc |

These keys follow [Microsoft's Windows shortcut definitions](https://support.microsoft.com/en-us/windows/keyboard-shortcuts-in-windows-dcc61a57-8ff0-cffe-9796-cb9706c75eec). Dictation, clipboard history and other Windows features may need to be enabled by the user first.

## FIX is a task, not an empty chat

1. Copy the error or code you want to work on.
2. Open **AI → Workflows → Fix**.
3. Check the project, exact harness/account and context. You can edit the excerpt or enter an English objective.
4. Choose **Start task**. The selected CLI receives that task, with the project and Git context.

If the clipboard is empty, FIX can offer the last failed local task from the same project. Empty FIX/EXPLAIN requests are refused. The deck never sends Ctrl+C to an arbitrary foreground window.

The terminal is the agent's interactive working session. Authentication, repository trust and CLI permission prompts may still require interaction. A started process does not prove the agent completed its task. The local receipts report launch or error, not invented progress or success.

**TEST in DEV** runs detected tests directly. **TEST + FIX in AI** prepares a testing-and-repair task for an agent. **Claude CLI** opens a general chat deliberately; **Fix** opens a contextual task.

## Profiles, languages and browsers

Use **Settings → Preferences** to choose the project, interface language, default harness, exact profile and browser for that account. Objectives and agent communication stay in English. The interface supports English, French and Windows language detection.

Named PowerShell functions such as `claude-work` and `codex-personal` are loaded in the user's configured PowerShell. Missing named profiles produce an error; the deck does not silently switch accounts. Choose `default` explicitly to use the base CLI.

**Work / Personal** is a quick switch between those two conventional profile names. Preferences also lists discovered custom profile names.

## Local files and updates

The default directory is `%LOCALAPPDATA%\AIDev\agentdeck`, without a space. When the generator runs inside a packaged Windows app, it records the physical directory Windows can actually read. `--data-dir` or `AI_DEV_AGENTDECK_DIR` can select another location outside the repository.

- `intents.json`: English task templates and harness choices.
- `state.json`: project, language, profile and browser preferences.
- `tools.json`: private installed-tool inventory.
- `receipts/`: observed task launch/error metadata.
- `last-failure.json`: tail of a failed local task, offered only for the matching project.
- `backups/`: previous generated profiles.

```powershell
python scripts/agent_deck.py --install --enable-shell
```

Installation restarts Stream Deck briefly, replaces the generated profile with a backup, and preserves its identity. **Re-scan** performs the same update. Generated archives and workstation data stay local and are excluded from the public source export.

## Execution boundaries

Agents retain their CLI permission checks. The prompts prohibit publishing and remote Git operations; that instruction is not a hard network firewall. The direct PUSH key asks for confirmation. Stash apply retains the selected stash. A missing project task reports the absence rather than inventing a command.

The optional Classic application remains available with `python launch.py` for its inventory and external-orchestrator features. Those features are not advertised as connected services or live telemetry on the physical deck.
