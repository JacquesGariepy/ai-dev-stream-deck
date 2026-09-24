param([string]$RuntimePath = $PSScriptRoot, [string]$ProfilePath = $PROFILE.CurrentUserAllHosts)
# Install a named module and an idempotent loader, preserving the user's profile.
$ErrorActionPreference = 'Stop'
$runtime = [IO.Path]::GetFullPath($RuntimePath)
if (-not (Test-Path -LiteralPath (Join-Path $runtime 'terminal.ps1') -PathType Leaf)) { throw 'The terminal integration is missing from the runtime.' }
$profileFile = [IO.Path]::GetFullPath($ProfilePath)
$profileDirectory = Split-Path -Parent $profileFile
$moduleDirectory = Join-Path $profileDirectory 'Modules\AIDevTerminal'
[IO.Directory]::CreateDirectory($moduleDirectory) | Out-Null
$module = @'
$runtime = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime.json') -Raw -Encoding UTF8 | ConvertFrom-Json).path
if (-not (Test-Path -LiteralPath (Join-Path $runtime 'terminal.ps1'))) { throw 'AI Dev terminal integration has moved. Run Terminal setup again.' }
. (Join-Path $runtime 'terminal.ps1')
Export-ModuleMember -Function Invoke-AIDevGit
'@
[IO.File]::WriteAllText((Join-Path $moduleDirectory 'AIDevTerminal.psm1'), $module, [Text.UTF8Encoding]::new($true))
[IO.File]::WriteAllText((Join-Path $moduleDirectory 'runtime.json'), (@{path=$runtime}|ConvertTo-Json), [Text.UTF8Encoding]::new($false))
$encoding = [Text.UTF8Encoding]::new($false)
$original = ''
if (Test-Path -LiteralPath $profileFile) {
    $bytes = [IO.File]::ReadAllBytes($profileFile)
    if ($bytes.Length -ge 4 -and $bytes[0] -eq 255 -and $bytes[1] -eq 254 -and $bytes[2] -eq 0 -and $bytes[3] -eq 0) { $encoding = [Text.Encoding]::UTF32 }
    elseif ($bytes.Length -ge 4 -and $bytes[0] -eq 0 -and $bytes[1] -eq 0 -and $bytes[2] -eq 254 -and $bytes[3] -eq 255) { $encoding = [Text.UTF32Encoding]::new($true, $true, $true) }
    elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 255 -and $bytes[1] -eq 254) { $encoding = [Text.Encoding]::Unicode }
    elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 254 -and $bytes[1] -eq 255) { $encoding = [Text.Encoding]::BigEndianUnicode }
    elseif ($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) { $encoding = [Text.UTF8Encoding]::new($true) }
    else {
        # Never replace invalid bytes in an existing ANSI profile with U+FFFD.
        try { [void][Text.UTF8Encoding]::new($false, $true).GetString($bytes) }
        catch {
            $encoding = [Text.Encoding]::GetEncoding([Globalization.CultureInfo]::CurrentCulture.TextInfo.ANSICodePage,
                [Text.EncoderFallback]::ExceptionFallback, [Text.DecoderFallback]::ExceptionFallback)
        }
    }
    $original = [IO.File]::ReadAllText($profileFile, $encoding)
}
$block = "# BEGIN AI Dev terminal integration`r`nImport-Module AIDevTerminal -ErrorAction SilentlyContinue`r`n# END AI Dev terminal integration"
$pattern = '(?ms)^# BEGIN AI Dev terminal integration\r?\n.*?^# END AI Dev terminal integration'
$updated = if ($original -match $pattern) { [regex]::Replace($original, $pattern, $block) } else { $original + "`r`n" + $block + "`r`n" }
if ($updated -ne $original) {
    if (Test-Path -LiteralPath $profileFile) {
        $backups = Join-Path $runtime 'backups'
        [IO.Directory]::CreateDirectory($backups) | Out-Null
        $backup = Join-Path $backups ('powershell-profile-' + [guid]::NewGuid().ToString('N') + '.ps1')
        Copy-Item -LiteralPath $profileFile -Destination $backup
    }
    [IO.File]::WriteAllText($profileFile, $updated, $encoding)
}
[pscustomobject]@{module='AIDevTerminal'; profile=$profileFile; activation='Import-Module AIDevTerminal'; changed=($updated -ne $original)} | ConvertTo-Json
