param(
    [Parameter(Mandatory)][ValidateSet('build','test','lint','dev','types','format')][string]$Kind,
    [Parameter(Mandatory)][string]$Project,
    [string]$StateDirectory = $(if ($env:AI_DEV_AGENTDECK_DIR) { $env:AI_DEV_AGENTDECK_DIR } else { $PSScriptRoot })
)
# Run conventional project tasks directly, with separate arguments and a visible
# result. A bounded local failure record can be used by FIX in the same project.
$ErrorActionPreference = 'Stop'
$executable = $null; $arguments = @(); $label = $null; $reason = $null
$tail = New-Object 'System.Collections.Generic.Queue[string]'
$projectPath = $Project
function Remember-Output([string]$line) {
    $tail.Enqueue($line)
    while ($tail.Count -gt 120) { [void]$tail.Dequeue() }
    Write-Host $line
}
function Find-Executable([string]$name) {
    $command = Get-Command $name -CommandType Application,ExternalScript -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) { return $command.Source }
    return $null
}
function Read-ProjectText([string]$path) {
    if (Test-Path -LiteralPath $path -PathType Leaf) { return (Get-Content -LiteralPath $path -Raw -Encoding UTF8) }
    return ''
}
function Save-Result([int]$code) {
    if (-not $StateDirectory) { return }
    try {
        New-Item -ItemType Directory -Path $StateDirectory -Force | Out-Null
        $result = [ordered]@{ project=$projectPath; kind=$Kind; command=$label; executable=$executable;
            arguments=@($arguments); exitCode=$code; endedAt=[DateTime]::UtcNow.ToString('o');
            outputTail=(@($tail.ToArray()) -join "`n") }
        $json = $result | ConvertTo-Json -Depth 5
        [IO.File]::WriteAllText((Join-Path $StateDirectory 'last-task.json'), $json, [Text.UTF8Encoding]::new($false))
        if ($code -ne 0) {
            [IO.File]::WriteAllText((Join-Path $StateDirectory 'last-failure.json'), $json, [Text.UTF8Encoding]::new($false))
        }
    } catch { Write-Warning ('Cannot save local task result: ' + $_.Exception.Message) }
}
try {
    if (-not (Test-Path -LiteralPath $Project -PathType Container)) { throw "Project folder does not exist: $Project" }
    $projectPath = (Get-Item -LiteralPath $Project).FullName
    Set-Location -LiteralPath $projectPath
    $aliases = @{
        build=@('build','compile','bundle'); test=@('test','tests','unit','check:test')
        lint=@('lint','check','eslint','ruff'); dev=@('dev','start','serve','run','watch')
        types=@('typecheck','type-check','types','tsc','mypy'); format=@('format','fmt','prettier')
    }
    if (Test-Path -LiteralPath 'package.json') {
        $package = Read-ProjectText 'package.json' | ConvertFrom-Json
        # npm/yarn/bun may be .cmd launchers. Safe script names also prevent
        # shell metacharacters from being interpreted by these launchers.
        $names = @($package.scripts.psobject.Properties.Name | Where-Object { $_ -cmatch '^[A-Za-z0-9][A-Za-z0-9:._-]*$' })
        $script = $null
        foreach ($candidate in $aliases[$Kind]) {
            $script = $names | Where-Object { $_ -ceq $candidate } | Select-Object -First 1
            if ($script) { break }
        }
        if (-not $script) {
            foreach ($candidate in $aliases[$Kind]) {
                $script = $names | Where-Object { $_.StartsWith($candidate + ':', [StringComparison]::Ordinal) } | Select-Object -First 1
                if ($script) { break }
            }
        }
        if ($script) {
            $manager = if (Test-Path -LiteralPath 'pnpm-lock.yaml') { 'pnpm' } elseif (Test-Path -LiteralPath 'yarn.lock') { 'yarn' } elseif ((Test-Path -LiteralPath 'bun.lock') -or (Test-Path -LiteralPath 'bun.lockb')) { 'bun' } else { 'npm' }
            $executable = Find-Executable $manager
            if (-not $executable) { throw "$manager is required for task '$script' but is not installed or not on PATH." }
            $arguments = @('run', $script); $label = "$manager run $script"
        } else { $reason = "No conventional $Kind script in package.json." }
    }
    $dotnetFiles = @(Get-ChildItem -LiteralPath $projectPath -File | Where-Object { $_.Extension -in @('.sln','.slnx') })
    if ($dotnetFiles.Count -eq 0) { $dotnetFiles = @(Get-ChildItem -LiteralPath $projectPath -File | Where-Object { $_.Extension -in @('.csproj','.fsproj','.vbproj') }) }
    if (-not $executable -and $dotnetFiles.Count -gt 0 -and $Kind -in @('build','test','format')) {
        if ($dotnetFiles.Count -ne 1) { throw 'Several .NET solutions/projects were found. Choose their folder or define an explicit project task.' }
        $executable = Find-Executable 'dotnet'
        if (-not $executable) { throw '.NET SDK is required for this project but was not found on PATH.' }
        $arguments = @($Kind, $dotnetFiles[0].FullName); $label = "dotnet $Kind $($dotnetFiles[0].Name)"
    }
    if (-not $executable -and (Test-Path -LiteralPath 'Cargo.toml') -and $Kind -in @('build','test','format','lint')) {
        $executable = Find-Executable 'cargo'
        if (-not $executable) { throw 'Cargo is required for this project but was not found on PATH.' }
        $arguments = @(if ($Kind -eq 'format') { 'fmt' } elseif ($Kind -eq 'lint') { 'clippy' } else { $Kind })
        $label = 'cargo ' + ($arguments -join ' ')
    }
    if (-not $executable -and (Test-Path -LiteralPath 'go.mod') -and $Kind -in @('build','test','format','lint')) {
        $executable = Find-Executable 'go'
        if (-not $executable) { throw 'Go is required for this project but was not found on PATH.' }
        $verb = if ($Kind -eq 'format') { 'fmt' } elseif ($Kind -eq 'lint') { 'vet' } else { $Kind }
        $arguments = @($verb,'./...'); $label = 'go ' + ($arguments -join ' ')
    }
    if (-not $executable -and $Kind -eq 'test') {
        $pyproject = Read-ProjectText 'pyproject.toml'
        $setup = Read-ProjectText 'setup.cfg'
        $testDirectory = if (Test-Path -LiteralPath 'tests' -PathType Container) { 'tests' } elseif (Test-Path -LiteralPath 'test' -PathType Container) { 'test' } else { $null }
        $pythonTests = @()
        if ($testDirectory) { $pythonTests += @(Get-ChildItem -LiteralPath $testDirectory -File -Recurse -Filter '*.py' | Where-Object { $_.Name -match '(^test_.*|.*_test)\.py$' }) }
        $pythonTests += @(Get-ChildItem -LiteralPath $projectPath -File -Filter 'test_*.py')
        $usesPytest = (Test-Path -LiteralPath 'pytest.ini') -or (Test-Path -LiteralPath 'conftest.py') -or $pyproject -match '(?m)^\s*\[tool\.pytest\.' -or $setup -match '(?m)^\s*\[tool:pytest\]'
        $usesUnittest = $false
        foreach ($file in $pythonTests) {
            $source = Read-ProjectText $file.FullName
            if ($source -match '(?m)^\s*(import pytest\b|from pytest\b)' -or $source -match '(?m)^(?:async )?def test_\w+\s*\(') { $usesPytest = $true }
            if ($source -match '\bunittest\b|\bTestCase\s*\)') { $usesUnittest = $true }
        }
        if ($usesPytest -or $usesUnittest) {
            $venv = Join-Path $projectPath '.venv\Scripts\python.exe'
            $executable = if (Test-Path -LiteralPath $venv -PathType Leaf) { $venv } else { Find-Executable 'python' }
            if (-not $executable) { throw 'Python is required for these tests but was not found on PATH.' }
            if ($usesPytest) { $arguments = @('-m','pytest'); $label = 'python -m pytest' }
            else { $arguments = @('-m','unittest','discover','-s', $(if ($testDirectory) { $testDirectory } else { '.' }),'-v'); $label = 'python -m unittest discover' }
        }
    }
    if (-not $executable) {
        if (-not $reason) { $reason = "No conventional $Kind task detected in $projectPath." }
        throw ($reason + ' Select a project with this task or add a conventional project script.')
    }
    Write-Host "[$($Kind.ToUpper())] $label" -ForegroundColor Cyan
    Write-Host "Project: $projectPath"
    $global:LASTEXITCODE = 0
    # Windows PowerShell emits native stderr as ErrorRecords; collect it without
    # treating each stderr line as a terminating PowerShell error.
    $ErrorActionPreference = 'Continue'
    & $executable @arguments 2>&1 | ForEach-Object { Remember-Output ([string]$_) }
    $taskExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    Write-Host "Exit code: $taskExit" -ForegroundColor $(if ($taskExit -eq 0) { 'Green' } else { 'Red' })
    Save-Result $taskExit
    exit $taskExit
} catch {
    Remember-Output ('Task could not run: ' + $_.Exception.Message)
    Save-Result 2
    exit 2
}
