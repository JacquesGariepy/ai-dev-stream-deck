param([Parameter(Mandatory)][string]$PythonPath, [Parameter(Mandatory)][string]$LauncherPath, [Parameter(Mandatory)][string]$OutputDirectory, [string]$ProfilesPath)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
if ($ProfilesPath) {
    foreach ($selection in @(Get-Content -LiteralPath $ProfilesPath -Raw | ConvertFrom-Json)) {
        if ($selection.id -cnotmatch '^[a-f0-9]{64}$') { throw 'Invalid profile shortcut identifier.' }
        $link = $shell.CreateShortcut((Join-Path $OutputDirectory ('profile-' + $selection.id + '.lnk')))
        $link.TargetPath = $PythonPath
        $link.Arguments = '"' + $LauncherPath + '" --profile-id ' + $selection.id
        $link.WorkingDirectory = Split-Path -Parent $LauncherPath
        $link.Save()
    }
}
foreach ($language in @('en','fr')) {
    $link = $shell.CreateShortcut((Join-Path $OutputDirectory ('deck-refresh-' + $language + '.lnk')))
    $link.TargetPath = $PythonPath
    $link.Arguments = '"' + $LauncherPath + '" --action deck-refresh --deck-language ' + $language
    $link.WorkingDirectory = Split-Path -Parent $LauncherPath
    $link.Save()
}
foreach ($action in @('mission','codex','claude','agy','context','status','files','terminal','guide','browser','web-work','web-personal','factory','factory-status','cursor','vscode','orca','monitor','resources','performance','system-info','capture','health','git','logs')) {
    $link = $shell.CreateShortcut((Join-Path $OutputDirectory ($action + '.lnk')))
    $link.TargetPath = $PythonPath
    $link.Arguments = '"' + $LauncherPath + '" --action ' + $action
    $link.WorkingDirectory = Split-Path -Parent $LauncherPath
    $link.Save()
}
$websites = @{
    chatgpt='https://chatgpt.com/';claude='https://claude.ai/';gemini='https://gemini.google.com/'
    perplexity='https://www.perplexity.ai/';github='https://github.com/'
    'github-pr'='https://github.com/pulls';'github-issues'='https://github.com/issues'
}
foreach ($site in $websites.Keys) {
    $link = $shell.CreateShortcut((Join-Path $OutputDirectory ('web-' + $site + '.lnk')))
    $link.TargetPath = $PythonPath
    $link.Arguments = '"' + $LauncherPath + '" --action web --url "' + $websites[$site] + '"'
    $link.WorkingDirectory = Split-Path -Parent $LauncherPath
    $link.Save()
}
