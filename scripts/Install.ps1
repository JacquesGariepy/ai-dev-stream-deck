param([string]$Python = 'python', [switch]$StreamDeck, [switch]$ElgatoMcp)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = (& $Python -c 'import sys; print(sys.executable)').Trim()
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ with Tk is required.' }
& $pythonPath (Join-Path $PSScriptRoot 'migrate_data.py')
if ($LASTEXITCODE -ne 0) { throw 'Data migration failed; existing data was retained.' }
& $pythonPath -c 'import sys, tkinter; assert sys.version_info >= (3,11)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ with Tk is required.' }
if ($ElgatoMcp) {
    & $pythonPath (Join-Path $PSScriptRoot 'setup_mcp.py')
    if ($LASTEXITCODE -ne 0) { throw 'Elgato MCP setup failed.' }
}
if ($StreamDeck) {
    & $pythonPath (Join-Path $PSScriptRoot 'stream_deck.py')
    if ($LASTEXITCODE -ne 0) { throw 'Stream Deck profile generation failed.' }
}
Write-Host "Run: `"$pythonPath`" `"$(Join-Path $repoRoot 'launch.py')`""
