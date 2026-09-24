param([Parameter(Mandatory)][string]$NpmPath, [Parameter(Mandatory)][string]$InstallDirectory)
$ErrorActionPreference = 'Stop'
& $NpmPath install --prefix $InstallDirectory --save-exact --ignore-scripts --no-audit --no-fund '@elgato/mcp-server@0.1.7'
if ($LASTEXITCODE -ne 0) { throw 'npm could not install the Elgato bridge.' }
