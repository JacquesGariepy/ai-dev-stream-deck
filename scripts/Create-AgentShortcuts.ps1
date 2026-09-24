param(
    [Parameter(Mandatory)][string]$ManifestPath,
    [Parameter(Mandatory)][string]$OutputDirectory
)
# Create the agentic deck shortcuts through Windows' native Shell Link API.
$ErrorActionPreference = 'Stop'
$entries = [object[]](Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json)
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
$expected = @{}
foreach ($entry in $entries) {
    if ($entry.name -cnotmatch '^ai-[a-z0-9][a-z0-9-]{0,80}$') { throw 'Invalid agent shortcut name.' }
    if (-not [IO.Path]::IsPathRooted([string]$entry.target) -or [IO.Path]::GetExtension([string]$entry.target) -ne '.exe') {
        throw ('Invalid target for ' + $entry.name)
    }
    if ($entry.arguments -cnotmatch '^-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "[^"]+\\agentdeck\\ai\.ps1" [a-z0-9-]+$') {
        throw ('Invalid arguments for ' + $entry.name)
    }
    if (-not [IO.Path]::IsPathRooted([string]$entry.workingDirectory)) { throw ('Invalid working directory for ' + $entry.name) }
    $fileName = ([string]$entry.name) + '.lnk'
    $path = Join-Path -Path $OutputDirectory -ChildPath $fileName
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    try {
        $link = $shell.CreateShortcut($path)
        $link.TargetPath = [string]$entry.target
        $link.Arguments = [string]$entry.arguments
        $link.WorkingDirectory = [string]$entry.workingDirectory
        $link.WindowStyle = 7
        $link.Save()
    } catch {
        throw ('Cannot create ' + $entry.name + ': ' + $_.Exception.Message)
    }
    $expected[$path.ToLowerInvariant()] = $true
}
Get-ChildItem -LiteralPath $OutputDirectory -Filter 'ai-*.lnk' | Where-Object {
    -not $expected.ContainsKey($_.FullName.ToLowerInvariant())
} | Remove-Item -Force
