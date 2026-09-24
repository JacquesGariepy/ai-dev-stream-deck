# Vanilla first run

The public repository is application source, not a copy of a workstation.

| Item | Fresh installation |
|---|---|
| Project | Empty; choose an existing directory before a mission or context capture |
| Harness and account | Detected locally; no maintainer account, credentials or profile functions are shipped |
| Orchestrator | None; optionally connect an external Factory or a custom executable / URL |
| Human language | Windows language, with French / English override |
| AI language | English, independently of the human interface |
| Browser | No saved choice; select an installed browser when opening a web button |
| Stream Deck | Optional; generate local shortcuts and import a profile for your own supported device |
| Desktop applications | Only detected installations receive generated application keys |
| MCP inventory | Reads declarations from supported local configuration files; never starts a server or exposes stored secrets |
| Usage / cost | Unknown unless measured; no invented telemetry |

Known harness adapters and common web destinations are optional capabilities. They do not install providers or select accounts. Custom PowerShell commands can be registered in private `profiles.local.json`; `Invoke-AiProfile` is an optional discovery convention, not a prerequisite. Custom orchestrators need their own command or URL; naming a tool does not imply a dedicated status adapter.

Configuration lives in `%LOCALAPPDATA%/AIDev`, or `AI_DEV_DATA_DIR` when explicitly set. A clone or source archive never includes that directory. Do not commit generated shortcuts, device profiles, local inventories, sessions or authentication data. Public exports use a source allowlist and screen for workstation paths and common credential formats.

Updating the source preserves existing local choices. To try a clean configuration without modifying an existing one, set `AI_DEV_DATA_DIR` to a separate empty directory for that process.

Supported scope remains Windows with Python/Tk. The Stream Deck layout adapts to Mini, Neo, +, original, MK.2 and XL grids (only the 15-key MK.2 is hardware-verified); `--grid COLSxROWS` covers other models. Multiple compatible devices require an explicit `--device-id` choice. The desktop panel works without Stream Deck or an installed AI harness.
