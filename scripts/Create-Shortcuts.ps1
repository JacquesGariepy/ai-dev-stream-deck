param([Parameter(Mandatory)][string]$PythonPath, [Parameter(Mandatory)][string]$LauncherPath, [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
foreach ($action in @('mission','codex','claude','agy','context','status','files','terminal','guide')) {
    $link = $shell.CreateShortcut((Join-Path $OutputDirectory ($action + '.lnk')))
    $link.TargetPath = $PythonPath
    $link.Arguments = '"' + $LauncherPath + '" --action ' + $action
    $link.WorkingDirectory = Split-Path -Parent $LauncherPath
    $link.Save()
}
