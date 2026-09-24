param(
    [Parameter(Mandatory)][ValidateSet('status','diff','log','fetch','pull','push','stage','switch','branch','stash','unstash')][string]$Action,
    [Parameter(Mandatory)][string]$Project
)
# Fixed Git commands with separate arguments. Changes selected on the deck are
# explained and confirmed in this terminal; no user input is evaluated as code.
$ErrorActionPreference = 'Stop'
function Confirm-Action([string]$description) {
    Write-Host $description -ForegroundColor Yellow
    return (Read-Host 'Confirm? (y/N; o = oui)') -match '^(?i:y|yes|o|oui)$'
}
function Read-Choice([object[]]$choices, [string]$prompt) {
    if ($choices.Count -eq 0) { throw 'No entries available for this action.' }
    for ($index=0; $index -lt $choices.Count; $index++) { Write-Host ('{0}. {1}' -f ($index+1), $choices[$index]) }
    $answer = Read-Host ($prompt + ' (number; Enter cancels)')
    if ([string]::IsNullOrWhiteSpace($answer)) { return $null }
    $number = 0
    if (-not [int]::TryParse($answer, [ref]$number) -or $number -lt 1 -or $number -gt $choices.Count) { throw 'Invalid selection. No Git changes were made.' }
    return [string]$choices[$number-1]
}
try {
    if (-not (Test-Path -LiteralPath $Project -PathType Container)) { throw "Project folder does not exist: $Project" }
    Set-Location -LiteralPath $Project
    $git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $git) { throw 'Git is not installed or is not on PATH.' }
    $inside = & $git.Source rev-parse --is-inside-work-tree 2>&1
    if ($LASTEXITCODE -ne 0 -or $inside -notcontains 'true') { throw "This folder is not a Git working tree: $Project" }
    $commands = @{
        status = @('status', '--short', '--branch')
        diff   = @('--no-pager', 'diff')
        log    = @('--no-pager', 'log', '--oneline', '--graph', '--decorate', '-n', '40')
        fetch  = @('fetch', '--all', '--prune')
        pull   = @('pull', '--ff-only')
    }
    $gitArgs = $commands[$Action]
    switch ($Action) {
        'push' {
            $branch = & $git.Source branch --show-current
            if (-not $branch) { throw 'Cannot push a detached HEAD. Switch to a branch first.' }
            $ErrorActionPreference = 'Continue'
            $ahead = & $git.Source rev-list --count '@{upstream}..HEAD' 2>$null
            $hasUpstream = $LASTEXITCODE -eq 0
            $ErrorActionPreference = 'Stop'
            if (-not $hasUpstream) { $ahead = '?'; $gitArgs = @('push', '--set-upstream', 'origin', 'HEAD') } else { $gitArgs = @('push') }
            if (-not (Confirm-Action "Push $branch ($ahead commit(s) ahead) from $Project")) { return }
        }
        'stage' {
            & $git.Source status --short
            if (-not (Confirm-Action 'Stage all changed, new and deleted files under this project folder?')) { return }
            $gitArgs = @('add','--all','--','.')
        }
        'switch' {
            $branches = @(& $git.Source for-each-ref '--format=%(refname:short)' refs/heads/)
            $selection = Read-Choice $branches 'Switch to local branch'
            if (-not $selection) { return }
            if (-not (Confirm-Action "Switch to branch '$selection'?")) { return }
            $gitArgs = @('switch','--',$selection)
        }
        'branch' {
            $name = Read-Host 'New branch name (Enter cancels)'
            if ([string]::IsNullOrWhiteSpace($name)) { return }
            if ($name.StartsWith('-') -or $name -match '@\{' -or $name -match '[\r\n]') { throw 'Invalid branch name.' }
            $ErrorActionPreference = 'Continue'
            & $git.Source check-ref-format --branch $name *> $null
            $valid = $LASTEXITCODE -eq 0
            $ErrorActionPreference = 'Stop'
            if (-not $valid) { throw 'Invalid Git branch name. No changes were made.' }
            if (-not (Confirm-Action "Create and switch to '$name' from the current commit?")) { return }
            $gitArgs = @('switch','--no-track','-c',$name)
        }
        'stash' {
            & $git.Source status --short
            if (-not (Confirm-Action 'Stash tracked changes in the repository? Untracked files will stay in place.')) { return }
            $gitArgs = @('stash','push','-m', ('AgentDeck ' + [DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss')))
        }
        'unstash' {
            $stashes = @(& $git.Source stash list '--format=%gd %s')
            $selection = Read-Choice $stashes 'Apply stash'
            if (-not $selection) { return }
            if ($selection -notmatch '^(stash@\{\d+\}) ') { throw 'Invalid stash selection.' }
            $reference = $Matches[1]
            if (-not (Confirm-Action "Apply $reference? The saved stash will be retained, including if conflicts occur.")) { return }
            $gitArgs = @('stash','apply',$reference)
        }
    }
    if (-not $gitArgs) { throw "Unsupported Git action: $Action" }
    Write-Host ('git ' + ($gitArgs -join ' ')) -ForegroundColor Cyan
    Write-Host "Project: $Project"
    $ErrorActionPreference = 'Continue'
    & $git.Source @gitArgs
    $code = $LASTEXITCODE
    Write-Host "Exit code: $code" -ForegroundColor $(if ($code -eq 0) { 'Green' } else { 'Red' })
    exit $code
} catch {
    Write-Host ('Git action could not run: ' + $_.Exception.Message) -ForegroundColor Red
    exit 2
}
