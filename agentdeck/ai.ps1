param([Parameter(Mandatory)][string]$Intent)
# Agent deck dispatcher. Runs hidden from a Stream Deck key (Windows PowerShell 5.1 compatible):
# captures context (project, selection, clipboard, Git), then opens a terminal where the harness
# is already working on the task. No application window in between.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms, Microsoft.VisualBasic

$Root = $PSScriptRoot
$Config = Get-Content -LiteralPath (Join-Path $Root 'intents.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$StateDir = Join-Path $env:LOCALAPPDATA 'AI Dev\agentdeck'
$StatePath = Join-Path $StateDir 'state.json'
New-Item -ItemType Directory -Force -Path (Join-Path $StateDir 'requests') | Out-Null

function Read-State {
    $state = @{ project = $Config.defaults.project; profile = $Config.defaults.profile; last = $null; recent = @() }
    if (Test-Path -LiteralPath $StatePath) {
        $saved = Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($name in 'project', 'profile', 'last', 'recent') { if ($null -ne $saved.$name) { $state[$name] = $saved.$name } }
    }
    return $state
}
function Save-State($state) {
    [IO.File]::WriteAllText($StatePath, ($state | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
}
function Notify([string]$Title, [string]$Text) {
    $icon = New-Object System.Windows.Forms.NotifyIcon
    $icon.Icon = [System.Drawing.SystemIcons]::Information
    $icon.Visible = $true
    $icon.ShowBalloonTip(4000, $Title, $Text, [System.Windows.Forms.ToolTipIcon]::Info)
    Start-Sleep -Milliseconds 4500
    $icon.Dispose()
}

Add-Type -Namespace AgentDeck -Name Win -MemberDefinition @'
[DllImport("user32.dll")] public static extern System.IntPtr GetForegroundWindow();
[DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(System.IntPtr h, System.Text.StringBuilder s, int n);
'@
function Get-ForegroundTitle {
    $buffer = New-Object System.Text.StringBuilder 512
    [void][AgentDeck.Win]::GetWindowText([AgentDeck.Win]::GetForegroundWindow(), $buffer, 512)
    return $buffer.ToString()
}
# "file.py - my-project - Visual Studio Code" -> the project folder, when it can be found.
function Resolve-EditorProject([string]$title, $state) {
    if ($title -notmatch ' - (Visual Studio Code|Cursor|Windsurf|VSCodium)') { return $null }
    $parts = $title -split ' - '
    if ($parts.Count -lt 2) { return $null }
    $name = ($parts[$parts.Count - 2] -replace '\s*\[.*\]$', '').Trim()
    $candidates = @($state.recent) + @($state.project)
    foreach ($root in $Config.defaults.roots) { $candidates += (Join-Path $root $name) }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Split-Path -Leaf $candidate) -eq $name -and (Test-Path -LiteralPath $candidate -PathType Container)) { return $candidate }
    }
    return $null
}
function Remember-Project($state, [string]$path) {
    $state.project = $path
    $state.recent = @(@($path) + @($state.recent | Where-Object { $_ -and $_ -ne $path }) | Select-Object -First 12)
}
function Open-Terminal([string]$Title, [string]$Project, [string]$Script, [string[]]$ScriptArgs) {
    $shell = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
    if (-not $shell) { $shell = (Get-Command powershell).Source }
    $quoted = ($ScriptArgs | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $wt = Get-Command wt -ErrorAction SilentlyContinue
    if ($wt) {
        $arguments = "-w agentdeck new-tab --title `"$Title`" -d `"$Project`" `"$shell`" -NoLogo -NoExit -File `"$Script`" $quoted"
        Start-Process -FilePath $wt.Source -ArgumentList $arguments
    } else {
        Start-Process -FilePath $shell -WorkingDirectory $Project -ArgumentList "-NoLogo -NoExit -File `"$Script`" $quoted"
    }
}
function Git-Text([string]$Project, [string[]]$GitArgs, [int]$MaxLines = 80) {
    try {
        $output = & git -C $Project @GitArgs 2>$null
        if ($LASTEXITCODE -ne 0) { return '' }
        return (@($output) | Select-Object -First $MaxLines) -join "`n"
    } catch { return '' }
}

$state = Read-State
try {
    switch -Regex ($Intent) {
        '^profile$' {
            $state.profile = if ($state.profile -eq 'work') { 'personal' } else { 'work' }
            Save-State $state
            Notify 'Agent deck' ("Profil actif : " + $state.profile.ToUpper())
            return
        }
        '^project$' {
            $detected = Resolve-EditorProject (Get-ForegroundTitle) $state
            $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
            $dialog.Description = 'Projet de travail pour le deck agentique'
            $dialog.SelectedPath = if ($detected) { $detected } else { $state.project }
            if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
                Remember-Project $state $dialog.SelectedPath; Save-State $state
                Notify 'Agent deck' ("Projet : " + $dialog.SelectedPath)
            }
            return
        }
        '^git-(status|diff|log|pull|push|fetch)$' {
            $project = $state.project
            $detected = Resolve-EditorProject (Get-ForegroundTitle) $state
            if ($detected) { $project = $detected }
            Open-Terminal ('git ' + $Matches[1]) $project (Join-Path $Root 'run-git.ps1') @($Matches[1], $project)
            return
        }
    }

    $harness = $null; $mode = 'interactive'; $prompt = ''; $title = $Intent.ToUpper()
    if ($Intent -match '^(claude|codex|agy)$') {
        $harness = $Intent
    } elseif ($Intent -eq 'continue') {
        if (-not $state.last) { Notify 'Agent deck' 'Aucune session precedente.'; return }
        $harness = $state.last; $mode = 'resume'; $title = 'CONTINUE ' + $harness.ToUpper()
    } else {
        $spec = $Config.intents.$Intent
        if (-not $spec) { throw "Intention inconnue : $Intent" }
        $harness = $spec.harness; $mode = $spec.mode; $title = $spec.title
        # Selection first (the editor still has focus: this script runs hidden).
        if ($spec.copySelection) {
            [System.Windows.Forms.SendKeys]::SendWait('^c')
            Start-Sleep -Milliseconds 300
        }
        $userInput = ''
        if ($spec.input) {
            $userInput = [Microsoft.VisualBasic.Interaction]::InputBox($spec.input, 'Agent deck - ' + $spec.title, '')
            if (-not $userInput.Trim()) { return }
        }
        $prompt = $spec.prompt.Replace('{input}', $userInput)
    }

    $project = $state.project
    $detected = Resolve-EditorProject (Get-ForegroundTitle) $state
    if ($detected) { $project = $detected }
    if (-not (Test-Path -LiteralPath $project -PathType Container)) { throw "Projet introuvable : $project (touche PROJET)" }
    Remember-Project $state $project

    if ($prompt) {
        $context = "`n`n---`nProject: $project"
        $branch = Git-Text $project @('branch', '--show-current') 1
        if ($branch) {
            $context += "`nBranch: $branch`nStatus:`n" + (Git-Text $project @('status', '--short') 60)
            $context += "`nDiff stat:`n" + (Git-Text $project @('diff', '--stat', 'HEAD') 40)
        }
        if ($spec.clipboard) {
            $clip = Get-Clipboard -Raw -ErrorAction SilentlyContinue
            if ($clip) {
                if ($clip.Length -gt 12000) { $clip = $clip.Substring(0, 12000) + "`n[truncated]" }
                $fence = '```'
                $context += "`n`nClipboard / selection:`n$fence`n$clip`n$fence"
            }
        }
        $prompt = $prompt + "`n`n" + $Config.guardrails + $context
    }

    $request = [ordered]@{ harness = $harness; profile = $state.profile; mode = $mode; prompt = $prompt; project = $project; title = $title }
    $requestPath = Join-Path $StateDir ('requests\' + [guid]::NewGuid().ToString() + '.json')
    [IO.File]::WriteAllText($requestPath, ($request | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
    $state.last = $harness
    Save-State $state
    Open-Terminal ($title + ' - ' + $harness + ' ' + $state.profile) $project (Join-Path $Root 'run-agent.ps1') @($requestPath)
} catch {
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Agent deck', 'OK', 'Error') | Out-Null
}
