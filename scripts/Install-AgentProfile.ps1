param(
    [Parameter(Mandatory)][string]$ProfilePath,
    [Parameter(Mandatory)][string]$ProfilesRoot,
    [Parameter(Mandatory)][string]$BackupRoot,
    [switch]$PrepareOnly
)
# Preparation happens on the profile volume with a short temporary name. Deep
# package cache paths exceed .NET Framework's MAX_PATH during ZIP extraction.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$root = [IO.Path]::GetFullPath($ProfilesRoot).TrimEnd('\')
$backup = [IO.Path]::GetFullPath($BackupRoot).TrimEnd('\')
if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw 'Stream Deck profile directory is missing.' }
[IO.Directory]::CreateDirectory($backup) | Out-Null
$stage = Join-Path $root ('.ad-' + [guid]::NewGuid().ToString('N').Substring(0,8))
if (-not $stage.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe staging path.' }
[IO.Directory]::CreateDirectory($stage) | Out-Null
$zip = [IO.Compression.ZipFile]::OpenRead([IO.Path]::GetFullPath($ProfilePath))
try {
    $top = @($zip.Entries | ForEach-Object { ($_.FullName -split '/')[0] } | Sort-Object -Unique)
    if ($top.Count -ne 1 -or $top[0] -notmatch '^[A-Fa-f0-9-]{36}\.sdProfile$') { throw 'Unexpected generated profile identity.' }
    foreach ($entry in $zip.Entries) {
        $destination = [IO.Path]::GetFullPath((Join-Path $stage $entry.FullName))
        if (-not $destination.StartsWith($stage + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe profile archive path.' }
    }
} finally { $zip.Dispose() }
[IO.Compression.ZipFile]::ExtractToDirectory([IO.Path]::GetFullPath($ProfilePath), $stage)
$stagedProfile = Join-Path $stage $top[0]
$manifest = Get-Content -LiteralPath (Join-Path $stagedProfile 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.Name -ne 'AI Dev Agentic') { throw 'This installer only handles AI Dev Agentic.' }
$target = [IO.Path]::GetFullPath((Join-Path $root $top[0]))
if (-not $target.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe destination.' }
if ($PrepareOnly) {
    [pscustomobject]@{ Stage=$stage; StagedProfile=$stagedProfile; Target=$target; BackupRoot=$backup } | ConvertTo-Json
    return
}
function Save-ProfileBackup([string]$directory, [string]$archive, [string]$profileName) {
    $zip = [IO.Compression.ZipFile]::Open($archive, [IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($file in Get-ChildItem -LiteralPath $directory -Recurse -File) {
            $relative = $file.FullName.Substring($directory.Length).TrimStart('\').Replace('\','/')
            [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $file.FullName,
                ($profileName + '/' + $relative), [IO.Compression.CompressionLevel]::Optimal) | Out-Null
        }
    } finally { $zip.Dispose() }
}
$executable = Join-Path $env:ProgramFiles 'Elgato\StreamDeck\StreamDeck.exe'
$running = @(Get-Process StreamDeck -ErrorAction SilentlyContinue)
$previous = $null
$completed = $false
try {
    if ($running.Count) {
        $running | Stop-Process
        foreach ($process in $running) {
            if (-not $process.WaitForExit(5000)) { throw 'Stream Deck did not stop. The installed profile has not been replaced.' }
        }
    }
    if (Test-Path -LiteralPath $target) {
        # Both moves stay on the profile volume. The previous profile remains
        # available for rollback even if creating the durable backup fails.
        $previous = Join-Path $root ('.ad-old-' + [guid]::NewGuid().ToString('N').Substring(0,8))
        if (-not $previous.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe backup staging path.' }
        Move-Item -LiteralPath $target -Destination $previous
        $archive = Join-Path $backup ((Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8) + '.streamDeckProfile')
        Save-ProfileBackup $previous $archive $top[0]
        Write-Output ('Previous profile backed up: ' + $archive)
    }
    Move-Item -LiteralPath $stagedProfile -Destination $target
    if (-not (Test-Path -LiteralPath (Join-Path $target 'manifest.json'))) { throw 'Profile installation did not complete.' }
    $completed = $true
    Write-Output ('Installed AI Dev Agentic: ' + $target)
} catch {
    if ($previous -and (Test-Path -LiteralPath $previous)) {
        if (Test-Path -LiteralPath $target) {
            $failed = Join-Path $root ('.ad-failed-' + [guid]::NewGuid().ToString('N').Substring(0,8))
            if (-not $failed.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe rollback staging path.' }
            Move-Item -LiteralPath $target -Destination $failed
        }
        Move-Item -LiteralPath $previous -Destination $target
    }
    throw
} finally {
    # Only this now-empty staging directory is removed. Previous and failed
    # generations are retained; no recursive delete touches Stream Deck data.
    if ($completed -and (Test-Path -LiteralPath $stage)) { Remove-Item -LiteralPath $stage }
    if (Test-Path -LiteralPath $executable) { Start-Process -FilePath $executable -WindowStyle Hidden }
}
