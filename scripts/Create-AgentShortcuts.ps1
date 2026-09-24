param(
    [Parameter(Mandatory)][string]$ManifestPath,
    [Parameter(Mandatory)][string]$OutputDirectory
)
# Native Shell Links must be reopened by Windows before they are published.
$ErrorActionPreference = 'Stop'
$entries = [object[]](Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json)
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
# Get-Item expands 8.3 names: comparing an unresolved TEMP path to FullName
# previously made cleanup delete the very links that had just been created.
$OutputDirectory = (Get-Item -LiteralPath $OutputDirectory).FullName
$ownershipPath = Join-Path $OutputDirectory '.agentdeck-shortcuts.json'
$previous = @()
if (Test-Path -LiteralPath $ownershipPath -PathType Leaf) {
    $previous = [object[]](Get-Content -LiteralPath $ownershipPath -Raw -Encoding UTF8 | ConvertFrom-Json)
}
$expected = @{}
foreach ($entry in $entries) {
    if ($entry.name -cnotmatch '^ai-[a-z0-9][a-z0-9-]{0,80}$') { throw 'Invalid agent shortcut name.' }
    if ($expected.ContainsKey([string]$entry.name)) { throw ('Duplicate shortcut: ' + $entry.name) }
    if (-not [IO.Path]::IsPathRooted([string]$entry.target) -or [IO.Path]::GetExtension([string]$entry.target) -ne '.exe') {
        throw ('Invalid target for ' + $entry.name)
    }
    if ($entry.arguments -cnotmatch '^-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "([^"\r\n]+\\ai\.ps1)" [a-z0-9-]+$' -or
        -not [IO.Path]::IsPathRooted([string]$Matches[1])) {
        throw ('Invalid arguments for ' + $entry.name)
    }
    if (-not [IO.Path]::IsPathRooted([string]$entry.workingDirectory)) { throw ('Invalid working directory for ' + $entry.name) }
    $expected[[string]$entry.name] = $true
}
$shell = New-Object -ComObject WScript.Shell
function Assert-Link($link, $entry) {
    if (-not [string]::Equals($link.TargetPath, [string]$entry.target, [StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals($link.Arguments, [string]$entry.arguments, [StringComparison]::Ordinal) -or
        -not [string]::Equals($link.WorkingDirectory, [string]$entry.workingDirectory, [StringComparison]::OrdinalIgnoreCase) -or
        $link.WindowStyle -ne 7) {
        throw ('Windows could not verify target, arguments and working directory for ' + $entry.name)
    }
}
foreach ($entry in $entries) {
    $path = Join-Path $OutputDirectory (([string]$entry.name) + '.lnk')
    $temporary = Join-Path $OutputDirectory ([guid]::NewGuid().ToString('N') + '.lnk')
    try {
        $link = $shell.CreateShortcut($temporary)
        $link.TargetPath = [string]$entry.target
        $link.Arguments = [string]$entry.arguments
        $link.WorkingDirectory = [string]$entry.workingDirectory
        $link.WindowStyle = 7
        $link.Save()
        Assert-Link ($shell.CreateShortcut($temporary)) $entry
        Move-Item -LiteralPath $temporary -Destination $path -Force
        Assert-Link ($shell.CreateShortcut($path)) $entry
    } catch {
        throw ('Cannot create ' + $entry.name + ': ' + $_.Exception.Message)
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
}
# Only remove links recorded by an earlier successful generation, and only
# when their contents still match. Leave other shortcuts in this folder alone.
foreach ($entry in $previous) {
    if ($entry.name -cnotmatch '^ai-[a-z0-9][a-z0-9-]{0,80}$' -or $expected.ContainsKey([string]$entry.name)) { continue }
    $path = Join-Path $OutputDirectory (([string]$entry.name) + '.lnk')
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
    $link = $shell.CreateShortcut($path)
    if ($link.TargetPath -ieq $entry.target -and $link.Arguments -ceq $entry.arguments -and $link.WorkingDirectory -ieq $entry.workingDirectory) {
        Remove-Item -LiteralPath $path -Force
    }
}
[IO.File]::WriteAllText($ownershipPath, (ConvertTo-Json -InputObject @($entries) -Depth 5), [Text.UTF8Encoding]::new($false))
