param([Parameter(Mandatory)][string]$RequestPath)
$ErrorActionPreference = 'Stop'
$request = Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $request.executable -PathType Leaf)) { throw 'Task executable is unavailable.' }
Set-Location -LiteralPath $request.project
$nativeArguments = @($request.arguments)
$global:LASTEXITCODE = 0
& $request.executable @nativeArguments
exit $LASTEXITCODE
