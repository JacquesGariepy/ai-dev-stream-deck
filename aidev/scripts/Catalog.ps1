# Shared discovery used both for inventory and immediately before launch.
function Get-AIDevCatalog {
    $rows = @()
    $known = [ordered]@{
        codex = @{ Names=@('codex'); Paths=@("$env:LOCALAPPDATA\Programs\OpenAI\Codex\bin\codex.exe") }
        claude = @{ Names=@('claude'); Paths=@("$env:USERPROFILE\.local\bin\claude.exe") }
        agy = @{ Names=@('agy'); Paths=@("$env:LOCALAPPDATA\agy\bin\agy.exe") }
        cursor = @{ Names=@('agent','cursor-agent'); Paths=@("$env:USERPROFILE\.local\bin\agent.exe") }
        gemini = @{ Names=@('gemini'); Paths=@() }
        opencode = @{ Names=@('opencode'); Paths=@() }
        aider = @{ Names=@('aider'); Paths=@() }
        copilot = @{ Names=@('copilot'); Paths=@() }
    }
    foreach ($tool in $known.Keys) {
        $executable = $null
        foreach ($name in $known[$tool].Names) {
            $resolved = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($resolved) { $executable = $resolved.Source; break }
        }
        if (-not $executable) {
            $executable = $known[$tool].Paths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
        }
        if ($executable) {
            $rows += [pscustomobject]@{tool=$tool;profile='default';command=$executable;executable=$executable;available=$true;initialized=$true;kind='application';directory=$null}
        }
    }
    if ((Get-Command Invoke-AiProfile -ErrorAction SilentlyContinue) -and
        (Get-Command Resolve-AiExecutable -ErrorAction SilentlyContinue) -and
        (Get-Command Get-AiProfileDir -ErrorAction SilentlyContinue)) {
        foreach ($candidate in Get-Command -CommandType Function,Alias) {
            $resolved = $candidate
            if ($candidate.CommandType -eq 'Alias') { $resolved = $candidate.ResolvedCommand }
            if (-not $resolved -or $resolved.CommandType -ne 'Function') { continue }
            $body = $resolved.ScriptBlock.Ast
            if ($body -is [System.Management.Automation.Language.FunctionDefinitionAst]) { $body = $body.Body }
            $calls = @($body.FindAll({param($node)
                $node -is [System.Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'Invoke-AiProfile'
            }, $false))
            if ($calls.Count -ne 1) { continue }
            $parameters = @{}
            $elements = $calls[0].CommandElements
            for ($i=1; $i -lt $elements.Count-1; $i++) {
                if ($elements[$i] -is [System.Management.Automation.Language.CommandParameterAst] -and
                    $elements[$i+1] -is [System.Management.Automation.Language.StringConstantExpressionAst]) {
                    $parameters[$elements[$i].ParameterName] = $elements[$i+1].Value
                }
            }
            if (-not $parameters.Tool -or -not $parameters.ProfileName) { continue }
            $tool = $parameters.Tool
            $profile = $parameters.ProfileName
            $executable = Resolve-AiExecutable -Tool $tool
            $directory = Get-AiProfileDir -Tool $tool -ProfileName $profile
            $rows += [pscustomobject]@{tool=$tool;profile=$profile;command=$candidate.Name;executable=$executable;available=[bool]$executable;initialized=[bool](Test-Path -LiteralPath $directory -PathType Container);kind='powershell';directory=$directory}
        }
    }
    # Additional launchers are explicit local registrations, never guessed from arbitrary function names.
    $runtimeRoot = if ($env:AI_DEV_DATA_DIR) { $env:AI_DEV_DATA_DIR } else { Join-Path $env:LOCALAPPDATA 'AIDev' }
    $registration = Join-Path $runtimeRoot 'profiles.local.json'
    if (Test-Path -LiteralPath $registration) {
        foreach ($item in @(Get-Content -LiteralPath $registration -Raw | ConvertFrom-Json)) {
            if (-not $item.tool -or -not $item.profile -or -not $item.command) { throw 'Invalid profiles.local.json entry' }
            $cmd = Get-Command -Name $item.command -CommandType Function,Alias,Application -ErrorAction SilentlyContinue | Where-Object Name -eq $item.command | Select-Object -First 1
            $rows += [pscustomobject]@{tool=[string]$item.tool;profile=[string]$item.profile;command=[string]$item.command;executable=$null;available=[bool]$cmd;initialized=$null;kind='powershell';directory=$null}
        }
    }
    return @($rows | Sort-Object tool,profile,command -Unique)
}
