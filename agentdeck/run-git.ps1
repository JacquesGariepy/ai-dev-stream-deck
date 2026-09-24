param([Parameter(Mandatory)][string]$Action, [Parameter(Mandatory)][string]$Project)
# Direct Git keys: one fixed command, visible, in the current project.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $Project
$commands = @{
    status = @('status', '--short', '--branch')
    diff   = @('diff')
    log    = @('--no-pager', 'log', '--oneline', '--graph', '--decorate', '-n', '40')
    fetch  = @('fetch', '--all', '--prune')
    pull   = @('pull', '--ff-only')
}
if ($Action -eq 'push') {
    $branch = git branch --show-current
    $ahead = git rev-list --count '@{upstream}..HEAD' 2>$null
    if ($LASTEXITCODE -ne 0) { $ahead = '?' ; $gitArgs = @('push', '--set-upstream', 'origin', 'HEAD') } else { $gitArgs = @('push') }
    Write-Host "Push $branch ($ahead commit(s) en avance) depuis $Project" -ForegroundColor Yellow
    if ((Read-Host 'Confirmer ? (o/N)') -notmatch '^[oOyY]') { return }
} else {
    $gitArgs = $commands[$Action]
}
Write-Host ('git ' + ($gitArgs -join ' ')) -ForegroundColor Cyan
& git @gitArgs
