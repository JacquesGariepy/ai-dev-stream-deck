param([Parameter(Mandatory)][string]$PythonPath, [Parameter(Mandatory)][string]$LauncherPath, [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
foreach ($action in @('mission','codex','claude','agy','context','status','files','terminal','guide','browser','web-work','web-personal')) {
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
