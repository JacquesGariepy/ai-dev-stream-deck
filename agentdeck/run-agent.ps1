param([Parameter(Mandatory)][string]$Request, [switch]$VerifyOnly)
# Runs with the user's PowerShell profile loaded so exact account wrappers exist.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'context.ps1')
$r = $null
$receiptDir = Join-Path (Split-Path -Parent (Split-Path -Parent $Request)) 'receipts'
try {
    $r = Get-Content -LiteralPath $Request -Raw -Encoding UTF8 | ConvertFrom-Json
    Test-AgentRequest $r
    $command = Get-AgentCommand $r.harness $r.profile $r.command
    $arguments = Get-AgentArguments $r
    if ($VerifyOnly) {
        [pscustomobject]@{status='verified';command=$command;project=$r.project;arguments=$arguments} | ConvertTo-Json -Depth 6
        return
    }
    Set-Location -LiteralPath $r.project
    Write-Host ('[' + $r.title + '] ' + $command + ' | ' + $r.mode + ' | ' + $r.project) -ForegroundColor Cyan
    if($r.prompt){Write-Host $r.prompt -ForegroundColor DarkGray}
    # Only metadata is retained; clipboard contents live in the temporary request.
    Remove-Item -LiteralPath $Request -Force
    Write-AgentReceipt $receiptDir $r 'launched'
    $statePath=Join-Path (Split-Path -Parent $receiptDir) 'state.json'
    if(Test-Path -LiteralPath $statePath){
        $state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $sessions=@($state.sessions | Where-Object {$_ -and -not ($_.project -eq $r.project -and $_.profile -eq $r.profile)})
        $sessions+=@([pscustomobject]@{project=$r.project;profile=$r.profile;harness=$r.harness;command=$r.command;time=[DateTime]::UtcNow.ToString('o')})
        $state | Add-Member -NotePropertyName sessions -NotePropertyValue @($sessions | Select-Object -Last 40) -Force
        [IO.File]::WriteAllText($statePath,($state|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
    }
    if ($PSVersionTable.PSVersion -ge [version]'7.3') {
        $PSNativeCommandArgumentPassing = 'Standard'
    } else {
        $arguments = @($arguments | ForEach-Object {Convert-LegacyNativeArgument $_})
    }
    $global:LASTEXITCODE = 0
    & $command @arguments
    if($LASTEXITCODE -ne 0){throw "The CLI exited with code $LASTEXITCODE. Check the terminal output."}
    # Zero exit status does not prove that the requested task was completed.
} catch {
    if ($r -and -not $VerifyOnly) {Write-AgentReceipt $receiptDir $r 'error' $_.Exception.Message}
    throw
}
