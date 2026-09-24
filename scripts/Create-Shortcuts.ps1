param(
    [Parameter(Mandatory)][string]$PythonPath,
    [Parameter(Mandatory)][string]$LauncherPath,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [Parameter(Mandatory)][string]$ManifestPath
)
# Creates one .lnk per Stream Deck Open key from the manifest written by stream_deck.py.
# Each entry is validated: a plain shortcut name and app-authored launcher arguments only.
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
$namePattern = '^[a-z0-9][a-z0-9-]{0,120}$'
$argumentPattern = '^--[a-z][a-z-]*( (--[a-z][a-z-]*|[A-Za-z0-9_.:/=-]+|"https://[A-Za-z0-9_.:/?&=%-]+"))*$'
foreach ($entry in @(Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json)) {
    if ($entry.name -cnotmatch $namePattern) { throw 'Invalid shortcut name.' }
    if ($entry.arguments -cnotmatch $argumentPattern) { throw ('Invalid shortcut arguments for ' + $entry.name) }
    $link = $shell.CreateShortcut((Join-Path $OutputDirectory ($entry.name + '.lnk')))
    $link.TargetPath = $PythonPath
    $link.Arguments = '"' + $LauncherPath + '" ' + $entry.arguments
    $link.WorkingDirectory = Split-Path -Parent $LauncherPath
    $link.Save()
}
