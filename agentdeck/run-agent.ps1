param([Parameter(Mandatory)][string]$Request)
# Runs inside the terminal tab, with the user's PowerShell profile loaded so that
# account wrappers such as claude-work or codex-personal are available.
$ErrorActionPreference = 'Stop'
$r = Get-Content -LiteralPath $Request -Raw -Encoding UTF8 | ConvertFrom-Json
Remove-Item -LiteralPath $Request -Force
Set-Location -LiteralPath $r.project

$command = $r.harness + '-' + $r.profile
if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { $command = $r.harness }
if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Harnais introuvable : $command" }

$arguments = @()
switch ($r.harness) {
    'claude' {
        switch ($r.mode) {
            'auto'     { $arguments = @('--permission-mode', 'bypassPermissions', '--disallowedTools', 'Bash(git push:*)') }
            'readonly' { $arguments = @('--permission-mode', 'plan') }
            'resume'   { $arguments = @('--continue') }
        }
        if ($r.prompt) { $arguments += @('--', $r.prompt) }
    }
    'codex' {
        switch ($r.mode) {
            'auto'     { $arguments = @('--full-auto') }            # workspace sandbox: edits and commits, no network, no push
            'readonly' { $arguments = @('--sandbox', 'read-only') }
            'resume'   { $arguments = @('resume', '--last') }
        }
        if ($r.prompt) { $arguments += @('--', $r.prompt) }
    }
    'agy' {
        if ($r.mode -eq 'readonly') { $arguments = @('--mode', 'plan') }
        if ($r.prompt) { $arguments += @('--prompt-interactive', $r.prompt) }
    }
}

Write-Host ('[' + $r.title + '] ' + $command + '  ' + $r.mode + '  ' + $r.project) -ForegroundColor Cyan
$global:LASTEXITCODE = 0
& $command @arguments
