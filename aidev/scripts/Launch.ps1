param([Parameter(Mandatory)][string]$RequestPath, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$request = Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json
. (Join-Path $PSScriptRoot 'Catalog.ps1')
$entry = Get-AIDevCatalog | Where-Object { $_.tool -eq $request.tool -and $_.profile -eq $request.profile -and $_.command -eq $request.command } | Select-Object -First 1
if (-not $entry) { throw 'The selected launcher is no longer present in PowerShell.' }
if (-not $entry.available) { throw 'The selected CLI is not available.' }
if ($CheckOnly) { @{entry=$entry;arguments=@($request.arguments)} | ConvertTo-Json -Depth 8 -Compress; return }
Set-Location -LiteralPath $request.project
$global:LASTEXITCODE = 0
$nativeArguments = @($request.arguments)
# Existing profile functions own account isolation and environment cleanup.
& $entry.command @nativeArguments
exit $LASTEXITCODE
