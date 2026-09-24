param([Parameter(Mandatory)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Catalog.ps1')
$result = @{entries=@(Get-AIDevCatalog);culture=(Get-Culture).Name;uiCulture=(Get-UICulture).Name;psVersion=$PSVersionTable.PSVersion.ToString()}
[IO.File]::WriteAllText($OutputPath, ($result | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
