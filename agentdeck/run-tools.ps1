param(
    [Parameter(Mandatory)][string]$Action,
    [string]$Query,
    [string]$Browser,
    [switch]$Plan
)
# Search and preferences run in native dialogs. No Python panel or shell-evaluated input.
$ErrorActionPreference = 'Stop'
$base = if ($env:AI_DEV_AGENTDECK_DIR) { $env:AI_DEV_AGENTDECK_DIR } else { $PSScriptRoot }
$statePath = Join-Path $base 'state.json'
$state = if (Test-Path -LiteralPath $statePath) { Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json } else { [pscustomobject]@{} }
$toolsPath = Join-Path $base 'tools.json'
$inventory = if (Test-Path -LiteralPath $toolsPath) { Get-Content -LiteralPath $toolsPath -Raw -Encoding UTF8 | ConvertFrom-Json } else { [pscustomobject]@{} }
$language = [string]$state.language
if ($language -notin @('fr','en')) { $language = if ((Get-UICulture).Name -like 'fr*') { 'fr' } else { 'en' } }
function L([string]$en, [string]$fr) { if ($language -eq 'fr') { return $fr }; return $en }
function Put-State([string]$name, $value) { $state | Add-Member -NotePropertyName $name -NotePropertyValue $value -Force }
function Save-PanelState {
    [IO.Directory]::CreateDirectory($base) | Out-Null
    [IO.File]::WriteAllText($statePath, ($state | ConvertTo-Json -Depth 15), [Text.UTF8Encoding]::new($false))
}
$sites = @{
    chatgpt='https://chatgpt.com/'; claude='https://claude.ai/'; gemini='https://gemini.google.com/'
    github='https://github.com/'; 'github-pr'='https://github.com/pulls'; 'github-issues'='https://github.com/issues'
    spotify='https://open.spotify.com/'; youtube='https://www.youtube.com/'; mdn='https://developer.mozilla.org/'
    mslearn='https://learn.microsoft.com/'; npm='https://www.npmjs.com/'; pypi='https://pypi.org/'
    perplexity='https://www.perplexity.ai/'; copilot='https://copilot.microsoft.com/'
}
$engines = @{
    google='https://www.google.com/search?q='; bing='https://www.bing.com/search?q='
    duckduckgo='https://duckduckgo.com/?q='; github='https://github.com/search?type=code&q='
    stackoverflow='https://stackoverflow.com/search?q='; youtube='https://www.youtube.com/results?search_query='
    perplexity='https://www.perplexity.ai/search?q='
}
function Browser-Choices {
    $result = [ordered]@{}
    if ($inventory.browsers) {
        foreach ($p in $inventory.browsers.psobject.Properties) {
            if (Test-Path -LiteralPath ([string]$p.Value) -PathType Leaf) { $result[$p.Name] = [string]$p.Value }
        }
    }
    return $result
}
function New-Panel([string]$title, [int]$height = 470) {
    Add-Type -AssemblyName System.Windows.Forms,System.Drawing
    [Windows.Forms.Application]::EnableVisualStyles()
    $form = New-Object Windows.Forms.Form
    $form.Text = 'AI Dev - ' + $title; $form.ClientSize = New-Object Drawing.Size(660,$height)
    $form.StartPosition = 'CenterScreen'; $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false; $form.MinimizeBox = $false
    $form.BackColor = [Drawing.Color]::FromArgb(24,28,36); $form.ForeColor = [Drawing.Color]::WhiteSmoke
    $form.Font = New-Object Drawing.Font('Segoe UI',10)
    return $form
}
function Add-Label($form,[string]$text,[int]$y) {
    $label = New-Object Windows.Forms.Label
    $label.Text=$text; $label.Location=New-Object Drawing.Point(22,$y); $label.Size=New-Object Drawing.Size(610,28)
    $form.Controls.Add($label); return $label
}
function Add-Combo($form,$items,[string]$value,[int]$x,[int]$y,[int]$width=280) {
    $combo = New-Object Windows.Forms.ComboBox
    $combo.DropDownStyle='DropDownList'; $combo.Location=New-Object Drawing.Point($x,$y)
    $combo.Size=New-Object Drawing.Size($width,30)
    foreach($item in $items) { [void]$combo.Items.Add([string]$item) }
    if($combo.Items.Contains($value)) {$combo.SelectedItem=$value} elseif($combo.Items.Count){$combo.SelectedIndex=0}
    $form.Controls.Add($combo); return $combo
}
function Add-Button($form,[string]$text,[int]$x,[int]$y,[string]$result) {
    $button = New-Object Windows.Forms.Button
    $button.Text=$text; $button.Location=New-Object Drawing.Point($x,$y); $button.Size=New-Object Drawing.Size(150,36)
    $button.FlatStyle='Flat'; $button.BackColor=[Drawing.Color]::FromArgb(43,52,67)
    if($result){$button.DialogResult=$result}
    $form.Controls.Add($button); return $button
}
function Saved-Browser {
    $context = if ($state.profile) { [string]$state.profile } else { 'default' }
    if ($state.browser -and $state.browser.psobject.Properties[$context]) { return [string]$state.browser.$context }
    return ''
}
function Save-Browser([string]$name) {
    $context = if ($state.profile) { [string]$state.profile } else { 'default' }
    if(-not $state.browser){Put-State 'browser' ([pscustomobject]@{})}
    $state.browser | Add-Member -NotePropertyName $context -NotePropertyValue $name -Force
    Save-PanelState
}
function Show-WebChoice([string]$title,[bool]$search,[string]$initial) {
    $choices = Browser-Choices
    $form = New-Panel $title 380
    [void](Add-Label $form (L 'Search text - review before sending' 'Recherche - verifier le texte avant envoi') 20)
    $input = New-Object Windows.Forms.TextBox
    $input.Multiline=$true; $input.ScrollBars='Vertical'; $input.Text=$initial
    $input.Location=New-Object Drawing.Point(22,52); $input.Size=New-Object Drawing.Size(610,125)
    $input.ReadOnly = -not $search
    $form.Controls.Add($input)
    [void](Add-Label $form ((L 'Browser / account: ' 'Navigateur / compte : ') + [string]$state.profile) 195)
    $selected = Add-Combo $form @($choices.Keys) (Saved-Browser) 22 225 290
    $remember = New-Object Windows.Forms.CheckBox
    $remember.Text = L 'Remember for this account' 'Memoriser pour ce compte'
    $remember.Location=New-Object Drawing.Point(332,225);$remember.Size=New-Object Drawing.Size(300,30)
    $form.Controls.Add($remember)
    $cancel=Add-Button $form (L 'Cancel' 'Annuler') 320 318 'Cancel'
    $open=Add-Button $form (L 'Open' 'Ouvrir') 482 318 'OK'
    $open.Enabled = $choices.Count -gt 0; $form.AcceptButton=$open;$form.CancelButton=$cancel
    $answer=$form.ShowDialog()
    if($answer -ne 'OK'){$form.Dispose();return $null}
    $value=[pscustomobject]@{query=$input.Text.Trim();browser=[string]$selected.SelectedItem}
    if($remember.Checked){Save-Browser $value.browser}
    $form.Dispose()
    return $value
}
function Open-Web([string]$url,[string]$name) {
    $uri = [uri]$url
    if($uri.Scheme -ne 'https' -or -not $uri.Host){throw 'Only HTTPS links are accepted.'}
    $choices = Browser-Choices
    if(-not $choices.Contains($name)){throw (L 'Choose an installed browser.' 'Choisis un navigateur installe.')}
    # A URL remains a single literal native argument; it is never evaluated as code.
    Start-Process -FilePath $choices[$name] -ArgumentList ('"' + $url.Replace('"','%22') + '"')
}
if($Action -match '^(search|web)-([a-z-]+)$'){
    $kind=$Matches[1];$key=$Matches[2];$isSearch=$kind -eq 'search'
    if(($isSearch -and -not $engines.ContainsKey($key)) -or (-not $isSearch -and -not $sites.ContainsKey($key))){throw 'Unknown search engine or website.'}
    if($Plan){
        if($isSearch -and [string]::IsNullOrWhiteSpace($Query)){throw 'Search query is required.'}
        $url=if($isSearch){$engines[$key]+[uri]::EscapeDataString($Query.Trim())}else{$sites[$key]}
        [pscustomobject]@{action=$Action;url=$url;browser=$Browser}|ConvertTo-Json -Compress
        return
    }
    $chosen = if($Browser){$Browser}else{Saved-Browser}
    $available = Browser-Choices
    if($chosen -and -not $available.Contains($chosen)){$chosen=''}
    if($isSearch -or -not $chosen){
        $initial=if($isSearch){if($Query){$Query}else{[string](Get-Clipboard -Raw -ErrorAction SilentlyContinue)}}else{$sites[$key]}
        if($initial.Length -gt 2000){$initial=$initial.Substring(0,2000)}
        $choice=Show-WebChoice ($key.ToUpper()) $isSearch $initial
        if(-not $choice){return}
        $chosen=$choice.browser;$Query=$choice.query
    }
    if($isSearch -and [string]::IsNullOrWhiteSpace($Query)){return}
    $url=if($isSearch){$engines[$key]+[uri]::EscapeDataString($Query.Trim())}else{$sites[$key]}
    Open-Web $url $chosen
    return
}
if($Action -in @('settings','browser','profiles')){
    if($Plan){[pscustomobject]@{action=$Action;dialog='preferences'}|ConvertTo-Json -Compress;return}
    $form=New-Panel (L 'Preferences' 'Reglages') 495
    [void](Add-Label $form (L 'Working project' 'Projet de travail') 20)
    $project=New-Object Windows.Forms.TextBox
    $project.Text=[string]$state.project;$project.Location=New-Object Drawing.Point(22,52);$project.Size=New-Object Drawing.Size(455,30)
    $form.Controls.Add($project)
    $browse=Add-Button $form (L 'Browse' 'Parcourir') 482 49 ''
    $browse.Add_Click({$folder=New-Object Windows.Forms.FolderBrowserDialog;$folder.SelectedPath=$project.Text;if($folder.ShowDialog() -eq 'OK'){$project.Text=$folder.SelectedPath};$folder.Dispose()})
    [void](Add-Label $form (L 'Interface language / agent harness' 'Langue interface / agent') 102)
    $lang=Add-Combo $form @('auto','fr','en') ([string]$state.language) 22 134
    $harnesses=@('claude','codex','agy')
    $harness=Add-Combo $form $harnesses ([string]$state.harness) 342 134
    [void](Add-Label $form (L 'Exact account profile / browser for this account' 'Profil de compte exact / navigateur de ce compte') 184)
    $profiles=@('default')+@($inventory.harnesses | ForEach-Object { $_.profile } | Where-Object {$_} | Sort-Object -Unique)
    $profile=Add-Combo $form $profiles ([string]$state.profile) 22 218
    $choices=Browser-Choices
    $browserItems=@('ask')+@($choices.Keys)
    $web=Add-Combo $form $browserItems (Saved-Browser) 342 218
    $profile.Add_SelectedIndexChanged({
        $key=[string]$profile.SelectedItem
        $saved=if($state.browser -and $state.browser.psobject.Properties[$key]){[string]$state.browser.$key}else{'ask'}
        if($web.Items.Contains($saved)){$web.SelectedItem=$saved}else{$web.SelectedItem='ask'}
    })
    $note=Add-Label $form (L 'AI objectives and replies use English. Desktop apps keep their own login.' 'Objectifs et reponses IA en anglais. Les apps gardent leur propre connexion.') 278
    $note.Height=54
    $note2=Add-Label $form (L 'Refresh the deck after changing the interface language or installing tools.' 'Actualise le deck apres un changement de langue ou une installation.') 334
    $note2.Height=48
    $cancel=Add-Button $form (L 'Cancel' 'Annuler') 320 435 'Cancel'
    $save=Add-Button $form (L 'Save' 'Enregistrer') 482 435 ''
    $save.Add_Click({
        if($project.Text -and -not (Test-Path -LiteralPath $project.Text -PathType Container)){
            [void][Windows.Forms.MessageBox]::Show((L 'Choose an existing project folder.' 'Choisis un dossier de projet existant.'));return
        }
        Put-State 'project' $project.Text
        Put-State 'profile' ([string]$profile.SelectedItem)
        Put-State 'harness' ([string]$harness.SelectedItem)
        Put-State 'language' ([string]$lang.SelectedItem)
        Save-Browser $(if($web.SelectedItem -eq 'ask'){''}else{[string]$web.SelectedItem})
        $form.DialogResult='OK';$form.Close()
    })
    $form.AcceptButton=$save;$form.CancelButton=$cancel
    [void]$form.ShowDialog();$form.Dispose();return
}
if($Action -eq 'shell-setup'){
    if($Plan){[pscustomobject]@{action=$Action;module='AIDevTerminal';activation='Import-Module AIDevTerminal';opensTerminal=$false}|ConvertTo-Json -Compress;return}
    $shells=@((Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'),[string]$inventory.powershell)|Where-Object {$_ -and (Test-Path -LiteralPath $_)}|Select-Object -Unique
    foreach($shell in $shells){
        & $shell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $base 'install-terminal.ps1') -RuntimePath $base | Out-Null
        if($LASTEXITCODE -ne 0){throw 'Terminal integration could not be installed. Check the PowerShell profile permissions.'}
    }
    $form=New-Panel (L 'PowerShell terminal setup' 'Integration du terminal PowerShell') 260
    $note=Add-Label $form (L 'Git keys now use the current folder at an empty PowerShell prompt. New sessions load the integration automatically.' 'Les touches Git utilisent le dossier courant dans PowerShell, sur une ligne vide. Les nouvelles sessions chargent automatiquement cette integration.') 20
    $note.Height=75
    $note2=Add-Label $form (L 'For a terminal already open, run this once:' 'Dans un terminal deja ouvert, execute une fois :') 103
    $command=New-Object Windows.Forms.TextBox;$command.Text='Import-Module AIDevTerminal';$command.ReadOnly=$true
    $command.Location=New-Object Drawing.Point(22,133);$command.Size=New-Object Drawing.Size(570,30);$form.Controls.Add($command)
    $copy=Add-Button $form (L 'Copy' 'Copier') 320 196 ''
    $copy.Add_Click({[Windows.Forms.Clipboard]::SetText('Import-Module AIDevTerminal')})
    $close=Add-Button $form (L 'Close' 'Fermer') 482 196 'Cancel';$form.CancelButton=$close
    [void]$form.ShowDialog();$form.Dispose();return
}
if($Action -in @('help','refresh')){
    $installPath=Join-Path $base 'installation.json'
    if(-not (Test-Path -LiteralPath $installPath)){throw 'Generate this profile again to register its source folder.'}
    $install=Get-Content -LiteralPath $installPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if($Action -eq 'help'){Start-Process -FilePath (Join-Path $install.source 'docs\CONTROL-PANEL.md');return}
    $arguments=@((Join-Path $install.source 'scripts\agent_deck.py'),'--install','--device-id',[string]$install.device_id,'--data-dir',$base)
    if($Plan){[pscustomobject]@{action=$Action;executable=$install.python;arguments=$arguments}|ConvertTo-Json -Depth 3 -Compress;return}
    if(-not(Test-Path -LiteralPath $install.python -PathType Leaf)){throw 'Python is missing. Reinstall the panel from the source folder.'}
    $quoted=($arguments|ForEach-Object{'"'+$_+'"'}) -join ' '
    Start-Process -FilePath $install.python -ArgumentList $quoted -WorkingDirectory $install.source -WindowStyle Hidden
    return
}
if($Action -match '^tool-(powertoys|devtoys)$'){
    $name=$Matches[1]
    $entry=@($inventory.apps)|Where-Object{$_.name -like ($name+'*')}|Select-Object -First 1
    if(-not $entry){throw 'Tool is not installed. Refresh after installation.'}
    if($Plan){[pscustomobject]@{action=$Action;app_id=$entry.app_id}|ConvertTo-Json -Compress;return}
    Start-Process explorer.exe ('"shell:AppsFolder\'+$entry.app_id+'"');return
}
throw ('Unknown utility: '+$Action)
