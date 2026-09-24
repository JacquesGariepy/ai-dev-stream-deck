# Engineering control panel priorities

## Available now

- Exact harness/account selection, generated from real PowerShell commands; stale selections never silently select another account.
- Local session lifecycle observations, start/end timestamps, readable receipts, Git snapshots, diagnostic follow-up objectives and an English handoff copied on demand.
- Canonical Factory task/attempt counts and pending decisions; direct access to its existing workbench.
- Tool and storage diagnostics, MCP configured-file checks, local branch/changes/worktree inspection and private error logs.
- Bilingual human controls, English agent instructions, explicit Chrome/Edge routing, and a space-free default data directory.
- Searchable installed-app and sanitized MCP inventories, generated paginated hardware keys, and explicit project task selection with real terminal exit codes.

## Proposed next increments (not implemented)

| Priority | Panel behavior | Stream Deck behavior | Evidence required |
|---|---|---|---|
| 1 | Queue requiring attention: approval requested, failed check, missing input | Live count and status color; press to inspect the exact item | Provider/Factory events with timestamps and an offline state; a native dynamic key integration, not imported static labels |
| 2 | Project/worktree switcher with branch and dirty-state preview | Recent projects and active branch | Validated local paths; preserve unstaged work; no automatic checkout or reset |
| 3 | Persist project-task exit history and cancellation controls | Show the last real task result and running state | Owned process tracking, bounded logs and explicit cancellation |
| 4 | Verifiable cost/token dashboard, separating providers, cache and estimates | Current measured usage and stale/unknown indicator | Provider-reported telemetry and coverage; never show missing cost as zero |
| 5 | Provider-specific resume/attach and interruption controls | Focus a running session; confirmed stop when supported | Valid provider session IDs and owned process trees; a PID alone is insufficient |

Keep destructive actions out of one-press shortcuts. Preparing a follow-up is distinct from resuming a conversation; a process exit is distinct from verified completion. The control panel should explain what was observed, when it was observed, and what action the engineer can take next.
