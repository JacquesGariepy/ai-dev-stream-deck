# Shared preparation. Never send keystrokes to an arbitrary foreground app.
function Get-AgentCommand([string]$Harness, [string]$Profile, [string]$CatalogCommand = '') {
    if($CatalogCommand){
        $catalogPath=Join-Path $PSScriptRoot 'tools.json'
        if($env:AI_DEV_AGENTDECK_DIR -and (Test-Path -LiteralPath (Join-Path $env:AI_DEV_AGENTDECK_DIR 'tools.json'))){
            $catalogPath=Join-Path $env:AI_DEV_AGENTDECK_DIR 'tools.json'
        }
        if(-not (Test-Path -LiteralPath $catalogPath)){throw 'The installed CLI catalog is missing. Refresh the deck.'}
        $catalog=Get-Content -LiteralPath $catalogPath -Raw -Encoding UTF8|ConvertFrom-Json
        $matching=@($catalog.harnesses | Where-Object {$_.tool -eq $Harness -and $_.profile -eq $Profile -and $_.command -eq $CatalogCommand})
        if(-not $matching){throw "The exact CLI command '$CatalogCommand' is absent from the installed catalog for $Harness / $Profile. Refresh the deck."}
        $name=$CatalogCommand
    }else{
        if ($Harness -notin @('claude', 'codex', 'agy')) { throw "Task launch is not supported for $Harness. Use its detected CLI button for an interactive session." }
        $name = if (-not $Profile -or $Profile -eq 'default') { $Harness } else { "$Harness-$Profile" }
    }
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "Profile command '$name' is unavailable in this PowerShell. Choose an installed profile, or 'default' to use the base CLI. No other account was selected."
    }
    return $name
}

function Get-AgentArguments($Request) {
    $result = @()
    switch ($Request.harness) {
        'claude' {
            switch ($Request.mode) {
                'auto' { $result = @('--permission-mode', 'acceptEdits') }
                'readonly' { $result = @('--permission-mode', 'plan') }
                'resume' { $result = @('--continue') }
            }
            if ($Request.prompt) { $result += @('--', [string]$Request.prompt) }
        }
        'codex' {
            switch ($Request.mode) {
                'auto' { $result = @('--sandbox', 'workspace-write', '--ask-for-approval', 'on-request') }
                'readonly' { $result = @('--sandbox', 'read-only', '--ask-for-approval', 'on-request') }
                'resume' { $result = @('resume', '--last') }
            }
            if ($Request.prompt) { $result += @('--', [string]$Request.prompt) }
        }
        'agy' {
            switch ($Request.mode) {
                'auto' { $result = @('--mode', 'accept-edits') }
                'readonly' { $result = @('--mode', 'plan') }
                'resume' { $result = @('--continue') }
            }
            if ($Request.prompt) { $result += @('--prompt-interactive', [string]$Request.prompt) }
        }
        default {
            if($Request.mode -ne 'interactive' -or $Request.prompt){throw "Automatic task arguments are not supported for $($Request.harness). Use its interactive CLI button."}
        }
    }
    return ,$result
}

function Test-AgentRequest($Request) {
    if (-not $Request -or -not $Request.project -or -not (Test-Path -LiteralPath $Request.project -PathType Container)) {
        throw 'Choose an existing project folder before starting an agent.'
    }
    if ($Request.mode -notin @('interactive', 'resume', 'auto', 'readonly')) { throw 'Invalid agent mode.' }
    if ($Request.mode -in @('auto', 'readonly') -and [string]::IsNullOrWhiteSpace($Request.prompt)) { throw 'The task is empty. Nothing was launched.' }
    if ($Request.intent -in @('fix', 'explain') -and [string]::IsNullOrWhiteSpace($Request.context) -and [string]::IsNullOrWhiteSpace($Request.objective)) {
        throw 'Copy the error or code first, or enter an English objective. Nothing was launched.'
    }
    if (([string]$Request.prompt).Length -gt 24000) { throw 'Task context is too long. Select a smaller excerpt.' }
    if($Request.harness -notin @('claude','codex','agy') -and ($Request.mode -ne 'interactive' -or $Request.prompt)){
        throw "Task or resume arguments are not supported for $($Request.harness). Open its exact CLI profile to continue interactively."
    }
    [void](Get-AgentCommand $Request.harness $Request.profile $Request.command)
}

function Convert-LegacyNativeArgument([string]$Value) {
    # Account wrappers forward this escaped string to their native CLI unchanged.
    return [regex]::Replace($Value, '(\\*)"', { param($m) $m.Groups[1].Value + $m.Groups[1].Value + '\"' })
}

function Join-WindowsArguments([string[]]$Values) {
    # Start-Process joins array elements without escaping them. Encode each
    # native argv element, including backslashes before quotes or a final quote.
    return (@($Values | ForEach-Object {
        $escaped=[regex]::Replace([string]$_, '(\\*)"', {param($m) $m.Groups[1].Value+$m.Groups[1].Value+'\"'})
        $escaped=[regex]::Replace($escaped, '(\\+)$', '$1$1')
        '"'+$escaped+'"'
    }) -join ' ')
}

function Write-AgentReceipt([string]$Directory, $Request, [string]$Status, [string]$ErrorText = '') {
    New-Item -ItemType Directory -Force -Path $Directory | Out-Null
    $id = if ($Request.id -match '^[a-zA-Z0-9-]+$') { $Request.id } else { [guid]::NewGuid().ToString() }
    $receipt = [ordered]@{
        id=$id; time=[DateTime]::UtcNow.ToString('o'); status=$Status
        intent=$Request.intent; harness=$Request.harness; profile=$Request.profile
        project=$Request.project; mode=$Request.mode; promptCharacters=([string]$Request.prompt).Length
    }
    if ($ErrorText) { $receipt.error = $ErrorText }
    [IO.File]::WriteAllText((Join-Path $Directory ($id + '.json')), ($receipt | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
}

function Show-AgentContext($Task, [string]$Language = 'en') {
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    $fr = $Language -like 'fr*'
    $form = New-Object Windows.Forms.Form
    $form.Text = 'Agent deck - ' + $Task.title; $form.Size = New-Object Drawing.Size(740, 620)
    $form.MinimumSize = $form.Size; $form.StartPosition = 'CenterScreen'
    $form.Font = New-Object Drawing.Font('Segoe UI', 10); $form.TopMost = $true
    $grid = New-Object Windows.Forms.TableLayoutPanel
    $grid.Dock = 'Fill'; $grid.Padding = New-Object Windows.Forms.Padding(18); $grid.ColumnCount = 1; $grid.RowCount = 10
    [void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 100)))
    foreach ($height in @(24, 36, 24, 36, 24, 82, 30, 145, 44, 42)) { [void]$grid.RowStyles.Add((New-Object Windows.Forms.RowStyle('Absolute', $height))) }
    $form.Controls.Add($grid)
    function Add-TaskLabel([string]$Text, [int]$Row) {
        $label = New-Object Windows.Forms.Label; $label.Text = $Text; $label.Dock = 'Fill'; $grid.Controls.Add($label, 0, $Row)
    }
    Add-TaskLabel $(if($fr){'Projet de travail'}else{'Working project'}) 0
    $projectRow = New-Object Windows.Forms.TableLayoutPanel; $projectRow.Dock='Fill'; $projectRow.ColumnCount=2
    [void]$projectRow.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 100)))
    [void]$projectRow.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Absolute', 100)))
    $project = New-Object Windows.Forms.TextBox; $project.Text=$Task.project; $project.Dock='Fill'
    $browse = New-Object Windows.Forms.Button; $browse.Text=$(if($fr){'Choisir...'}else{'Browse...'}); $browse.Dock='Fill'
    $browse.Add_Click({
        $folder = New-Object Windows.Forms.FolderBrowserDialog; $folder.SelectedPath=$project.Text
        if($folder.ShowDialog() -eq 'OK'){$project.Text=$folder.SelectedPath}; $folder.Dispose()
    })
    $projectRow.Controls.Add($project,0,0);$projectRow.Controls.Add($browse,1,0);$grid.Controls.Add($projectRow,0,1)
    Add-TaskLabel $(if($fr){'Agent et profil exact'}else{'Agent and exact profile'}) 2
    $command = New-Object Windows.Forms.ComboBox; $command.Dock='Fill'; $command.DropDownStyle='DropDownList'
    $choices = @()
    foreach($h in @('claude','codex','agy')) {
        if(Get-Command $h -ErrorAction SilentlyContinue){$choices += [pscustomobject]@{label="$h / default";harness=$h;profile='default'}}
        foreach($c in @(Get-Command "$h-*" -CommandType Function,Alias -ErrorAction SilentlyContinue)) {
            $choices += [pscustomobject]@{label=$c.Name;harness=$h;profile=$c.Name.Substring($h.Length+1)}
        }
    }
    $selectedName=if($Task.profile -eq 'default'){'{0} / default' -f $Task.harness}else{'{0}-{1}' -f $Task.harness,$Task.profile}
    if(-not ($choices | Where-Object {$_.label -eq $selectedName})) {
        $choices = @([pscustomobject]@{label=$selectedName;harness=$Task.harness;profile=$Task.profile}) + $choices
    }
    foreach($c in $choices){[void]$command.Items.Add($c.label)}
    $command.SelectedItem=$selectedName; $grid.Controls.Add($command,0,3)
    Add-TaskLabel $(if($fr){'Objectif en anglais (Win + H pour dicter)'}else{'Objective in English (Win + H to dictate)'}) 4
    $objective=New-Object Windows.Forms.TextBox; $objective.Multiline=$true; $objective.Dock='Fill'; $objective.ScrollBars='Vertical'; $objective.Text=$Task.objective
    $grid.Controls.Add($objective,0,5)
    $include=New-Object Windows.Forms.CheckBox; $include.Dock='Fill'
    $include.Text=$(if($fr){'Inclure : '}else{'Include: '}) + $Task.contextSource
    $include.Checked= -not [string]::IsNullOrWhiteSpace($Task.context); $grid.Controls.Add($include,0,6)
    $context=New-Object Windows.Forms.TextBox; $context.Multiline=$true; $context.Dock='Fill'; $context.ScrollBars='Both'; $context.Text=$Task.context
    $context.Font=New-Object Drawing.Font('Consolas',9); $grid.Controls.Add($context,0,7)
    Add-TaskLabel $(if($fr){'Session interactive avec la tache prechargee. Les autorisations du CLI restent actives.'}else{'Interactive session with the task loaded. CLI permission checks remain active.'}) 8
    $buttons=New-Object Windows.Forms.FlowLayoutPanel; $buttons.Dock='Fill'; $buttons.FlowDirection='RightToLeft'
    $launch=New-Object Windows.Forms.Button; $launch.Width=140; $launch.Height=32; $launch.Text=$(if($fr){'Lancer la tache'}else{'Start task'})
    $cancel=New-Object Windows.Forms.Button; $cancel.Width=100; $cancel.Height=32; $cancel.Text=$(if($fr){'Annuler'}else{'Cancel'}); $cancel.DialogResult='Cancel'
    $buttons.Controls.Add($launch);$buttons.Controls.Add($cancel);$grid.Controls.Add($buttons,0,9); $form.CancelButton=$cancel
    $launch.Add_Click({
        try {
            $pick=$choices | Where-Object {$_.label -eq $command.SelectedItem} | Select-Object -First 1
            if(-not $pick){throw 'Select an installed agent profile.'}
            [void](Get-AgentCommand $pick.harness $pick.profile)
            if(-not (Test-Path -LiteralPath $project.Text -PathType Container)){throw 'Choose an existing project folder.'}
            $inputContext=if($include.Checked){$context.Text}else{''}
            if($Task.intent -in @('fix','explain') -and -not $inputContext.Trim() -and -not $objective.Text.Trim()) {
                throw $(if($fr){'Copie une erreur ou du code, ou saisis un objectif en anglais.'}else{'Paste an error or code, or enter an English objective.'})
            }
            if($Task.intent -in @('ask','plan') -and -not $objective.Text.Trim()){throw 'Enter an objective in English.'}
            $form.Tag=[pscustomobject]@{project=$project.Text;harness=$pick.harness;profile=$pick.profile;objective=$objective.Text;context=$inputContext}
            $form.DialogResult='OK';$form.Close()
        } catch {[void][Windows.Forms.MessageBox]::Show($_.Exception.Message, $form.Text,'OK','Warning')}
    })
    try { if($form.ShowDialog() -eq 'OK'){return $form.Tag};return $null } finally {$form.Dispose()}
}
