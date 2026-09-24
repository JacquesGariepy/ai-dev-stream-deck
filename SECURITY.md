# Security and privacy

Do not attach real profile directories, credentials, mission receipts, discovery output, generated Stream Deck archives or environment dumps to public issues.

Runtime data is private by default and stored outside the source checkout. The source export is an allowlist, not a backup tool. Review source changes and the staged Git diff before publication.

Discovery loads your existing PowerShell startup profile. Only trust startup scripts and explicitly registered launch commands you would run yourself. The app does not bypass provider permission prompts. An objective is passed as one argument via a JSON request file; it is never interpolated into shell code.

This project does not execute arbitrary MCP tool requests itself; optional MCP actions are governed by the connected harness and Stream Deck. Expose only intended actions in MCP Deck.

For a suspected vulnerability, use GitHub private vulnerability reporting if enabled. Do not post exploit details or secrets in a public issue.
