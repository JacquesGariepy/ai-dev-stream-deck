# Dot-sourced by AIDevTerminal. The key handlers exist only at a PSReadLine
# prompt: no command text is sent into editors, running agents or other apps.
$script:AIDevRuntime = $PSScriptRoot

function Invoke-AIDevGit {
    [CmdletBinding()]
    param([Parameter(Mandatory)][ValidateSet('status','diff','log','fetch','pull','push','stage','switch','branch','stash','unstash')][string]$Action)
    $location=Get-Location
    if($location.Provider.Name -ne 'FileSystem'){throw 'Git requires a filesystem directory in the current PowerShell session.'}
    # Resolve the actual location at execution time, never a deck settings path.
    & (Join-Path $script:AIDevRuntime 'run-git.ps1') -Action $Action -Project $location.ProviderPath
}

function Invoke-AIDevGitPromptAction {
    param(
        [Parameter(Mandatory)][ValidateSet('status','diff','log','fetch','pull','push','stage','switch','branch','stash','unstash')][string]$Action,
        [scriptblock]$ReadBuffer = {
            $line='';$cursor=0
            [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line,[ref]$cursor)
            return $line
        },
        [scriptblock]$InsertLine = {param($text) [Microsoft.PowerShell.PSConsoleReadLine]::Insert($text)},
        [scriptblock]$SubmitLine = {[Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()},
        [scriptblock]$RejectLine = {[Microsoft.PowerShell.PSConsoleReadLine]::Ding()}
    )
    $buffer=[string](& $ReadBuffer)
    if($buffer.Length -ne 0){ & $RejectLine; return $false }
    # The action is a ValidateSet value, not executable user text. PSReadLine
    # submits it through this shell's normal interactive evaluation/history.
    & $InsertLine ('Invoke-AIDevGit -Action '+$Action)
    & $SubmitLine
    return $true
}

$script:AIDevTerminalBindings=@()
try {
    Import-Module PSReadLine -ErrorAction Stop
    $actions=@('status','diff','log','fetch','pull','push','stage','switch','branch','stash','unstash')
    $current=@(Get-PSReadLineKeyHandler)
    for($index=0;$index -lt $actions.Count;$index++){
        $boundAction=$actions[$index]
        $chord='Ctrl+Alt+F'+(13+$index)
        $name='AIDevGit'+$boundAction
        $existing=@($current|Where-Object {$_.Key -eq $chord})
        if($existing.Count -gt 0 -and $existing[0].Function -ne $name){
            Write-Warning ("AIDevTerminal: $chord already belongs to " + $existing[0].Function + '. Its binding was preserved.')
            $script:AIDevTerminalBindings+=@([pscustomobject]@{action=$boundAction;chord=$chord;status='conflict'})
            continue
        }
        $invokeHandler=${function:Invoke-AIDevGitPromptAction}
        $handler={param($key,$arg) [void](& $invokeHandler -Action $boundAction)}.GetNewClosure()
        Set-PSReadLineKeyHandler -Chord $chord -BriefDescription $name -ScriptBlock $handler
        $script:AIDevTerminalBindings+=@([pscustomobject]@{action=$boundAction;chord=$chord;status='registered'})
    }
} catch {
    Write-Warning ('AIDevTerminal hotkeys are unavailable in this shell: '+$_.Exception.Message)
}
