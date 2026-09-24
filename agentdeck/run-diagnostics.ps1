param(
    [Parameter(Mandatory)][ValidateSet('ports','processes','connection','dns','routes','path','disk','startup','wsl','docker','longpaths')][string]$Action,
    [string]$Project,
    [switch]$Plan,
    [string]$HostName,
    [ValidateRange(1,65535)][int]$Port = 443
)
# Read-only workstation diagnostics. Plans are resolved before any discovery,
# prompts, subprocesses or network calls so routing can be verified safely.
$specifications = @{
    ports=@{title='Listening ports and owning processes'; commands=@('Get-NetTCPConnection -State Listen','Get-NetUDPEndpoint','Get-Process'); prerequisites=@('NetTCPIP or netstat.exe')}
    processes=@{title='Processes and parent processes'; commands=@('Get-CimInstance Win32_Process (PID, parent PID, name only)'); prerequisites=@('CIM or Get-Process')}
    connection=@{title='TCP connection test'; commands=@('Test-NetConnection -ComputerName <host> -Port <port>'); prerequisites=@('NetTCPIP or .NET TcpClient')}
    dns=@{title='DNS lookup'; commands=@('Resolve-DnsName -Name <host>'); prerequisites=@('DnsClient or .NET DNS')}
    routes=@{title='Network addresses, gateways and DNS servers'; commands=@('Get-NetIPConfiguration','Get-NetRoute (default routes)','Get-DnsClientServerAddress'); prerequisites=@('NetTCPIP and DnsClient, or ipconfig.exe and route.exe')}
    path=@{title='PATH entries, missing folders and duplicates'; commands=@('Inspect PATH entries only; test each directory'); prerequisites=@()}
    disk=@{title='Volume capacity and free space'; commands=@('System.IO.DriveInfo.GetDrives (no file scan)'); prerequisites=@()}
    startup=@{title='Startup entries without command lines'; commands=@('Read Run and RunOnce registry entry names','List startup-folder item names'); prerequisites=@()}
    wsl=@{title='WSL status and distributions'; commands=@('wsl.exe --status','wsl.exe --list --verbose'); prerequisites=@('wsl.exe')}
    docker=@{title='Docker containers and resource usage'; commands=@('docker.exe ps --all (names, images, status and ports)','docker.exe stats --no-stream'); prerequisites=@('docker.exe and a running Docker engine')}
    longpaths=@{title='Windows and Git long-path settings'; commands=@('Read HKLM FileSystem LongPathsEnabled','git config --show-origin --get core.longpaths'); prerequisites=@('git.exe for Git setting')}
}
$specification = $specifications[$Action]
$portSupplied = $PSBoundParameters.ContainsKey('Port')
if ($Plan) {
    [ordered]@{schemaVersion=1; action=$Action; title=$specification.title; commands=@($specification.commands);
        prerequisites=@($specification.prerequisites); readOnly=$true;
        hostRequired=($Action -in @('connection','dns')); hostName=$HostName;
        port=$(if ($Action -eq 'connection') { $Port } else { $null });
        promptForPort=($Action -eq 'connection' -and -not $portSupplied)} | ConvertTo-Json -Depth 5
    return
}
$ErrorActionPreference = 'Stop'
function Show-Rows($rows) {
    if (@($rows).Count -eq 0) { Write-Host 'No matching entries were found.'; return }
    $rows | Format-Table -AutoSize -Wrap | Out-Host
}
function Find-Native([string]$name) {
    return (Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1)
}
function Require-Native([string]$name) {
    $command = Find-Native $name
    if (-not $command) { throw "$name was not found. Install it or add it to PATH, then try again." }
    return $command.Source
}
function Invoke-NativeCapture([string]$executable, [string[]]$arguments) {
    $oldPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $global:LASTEXITCODE = 0
        $lines = @(& $executable @arguments 2>&1 | ForEach-Object { [string]$_ })
        return [pscustomobject]@{lines=$lines; exitCode=$LASTEXITCODE}
    } finally { $ErrorActionPreference = $oldPreference }
}
function Run-Native([string]$executable, [string[]]$arguments) {
    $result = Invoke-NativeCapture $executable $arguments
    foreach ($line in $result.lines) { Write-Host $line }
    if ($result.exitCode -ne 0) { throw ((Split-Path -Leaf $executable) + ' failed with exit code ' + $result.exitCode + '. See the output above.') }
}
function Get-ProcessNames {
    $names = @{}
    foreach ($process in Get-Process -ErrorAction Stop) { $names[$process.Id] = $process.ProcessName }
    return $names
}
function Select-Host {
    if ([string]::IsNullOrWhiteSpace($HostName)) { $script:HostName = Read-Host 'Host name or IP address (Enter cancels)' }
    if ([string]::IsNullOrWhiteSpace($HostName)) { return $false }
    $script:HostName = $HostName.Trim()
    if ($HostName.Length -gt 253 -or [Uri]::CheckHostName($HostName.Trim('[',']')) -eq [UriHostNameType]::Unknown) {
        throw 'Enter a host name or IP address without a URL scheme, path or port.'
    }
    return $true
}
try {
    Write-Host ('[DIAGNOSTICS] ' + $specification.title) -ForegroundColor Cyan
    switch ($Action) {
        'ports' {
            $names = Get-ProcessNames
            $rows = @()
            try {
                if (-not (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue)) { throw 'NetTCPIP commands are unavailable.' }
                $tcp = @(Get-NetTCPConnection -State Listen -ErrorAction Stop)
                $udp = @(Get-NetUDPEndpoint -ErrorAction Stop)
                foreach ($entry in $tcp + $udp) {
                    $rows += [pscustomobject]@{Protocol=$(if ($null -ne $entry.State) {'TCP'} else {'UDP'});
                        Address=$entry.LocalAddress; Port=$entry.LocalPort; PID=$entry.OwningProcess;
                        Process=$(if ($names.ContainsKey([int]$entry.OwningProcess)) {$names[[int]$entry.OwningProcess]} else {'exited / unavailable'})}
                }
            } catch {
                Write-Warning ('NetTCPIP unavailable: ' + $_.Exception.Message + ' Using netstat instead.')
                $result = Invoke-NativeCapture (Require-Native 'netstat.exe') @('-ano')
                if ($result.exitCode -ne 0) { throw ('netstat failed: ' + ($result.lines -join ' ')) }
                $unrecognized = $false
                foreach ($line in $result.lines) {
                    $protocol = $null
                    if ($line -match '^\s*(TCP)\s+(\S+):(\d+)\s+(\S+)\s+(\S+)\s+(\d+)\s*$') {
                        # A listening socket has no remote peer (:0), regardless
                        # of the localized spelling of its state column.
                        $fields = @($Matches[1],$Matches[2],$Matches[3],$Matches[4],$Matches[5],$Matches[6])
                        if ($fields[4] -eq 'LISTENING' -or $fields[3] -match '^(?:0\.0\.0\.0|\[?::\]?|\*):0$') {
                            $protocol=$fields[0]; $address=$fields[1]; $localPort=[int]$fields[2]; $owner=[int]$fields[5]
                        }
                    } elseif ($line -match '^\s*(UDP)\s+(\S+):(\d+)\s+\S+\s+(\d+)\s*$') {
                        $protocol=$Matches[1]; $address=$Matches[2]; $localPort=[int]$Matches[3]; $owner=[int]$Matches[4]
                    } elseif ($line -match '^\s*(TCP|UDP)\s+') { $unrecognized = $true }
                    if ($protocol) {
                        $rows += [pscustomobject]@{Protocol=$protocol; Address=$address; Port=$localPort; PID=$owner;
                            Process=$(if ($names.ContainsKey($owner)) {$names[$owner]} else {'exited / unavailable'})}
                    }
                }
                if ($unrecognized) {
                    Write-Warning 'Some netstat rows could not be interpreted. Full endpoint output follows.'
                    foreach ($line in $result.lines) { Write-Host $line }
                }
                if ($rows.Count -eq 0 -and ($result.lines -join ' ') -match '(?i)access.+denied|acces.+refus') { throw 'netstat access was denied.' }
            }
            Show-Rows ($rows | Sort-Object Port,Protocol,PID)
        }
        'processes' {
            try {
                $processes = @(Get-CimInstance -ClassName Win32_Process -Property ProcessId,ParentProcessId,Name -ErrorAction Stop)
                if ($processes.Count -eq 0) { throw 'CIM returned no process information.' }
                $names = @{}; foreach ($process in $processes) { $names[[int]$process.ProcessId] = $process.Name }
                Show-Rows ($processes | Sort-Object Name,ProcessId | ForEach-Object {
                    [pscustomobject]@{PID=$_.ProcessId; ParentPID=$_.ParentProcessId; Name=$_.Name;
                        Parent=$(if ($names.ContainsKey([int]$_.ParentProcessId)) {$names[[int]$_.ParentProcessId]} else {'exited / unavailable'})}
                })
            } catch {
                Write-Warning ('Parent process information is unavailable: ' + $_.Exception.Message)
                $rows = @(Get-Process -ErrorAction Stop | Sort-Object ProcessName,Id | Select-Object @{n='PID';e={$_.Id}},ProcessName)
                if ($rows.Count -eq 0) { throw 'No process information could be read.' }
                Show-Rows $rows
            }
        }
        'connection' {
            if (-not (Select-Host)) { return }
            if (-not $portSupplied) {
                $answer = Read-Host 'TCP port (Enter = 443)'
                if (-not [string]::IsNullOrWhiteSpace($answer)) {
                    $selectedPort = 0
                    if (-not [int]::TryParse($answer, [ref]$selectedPort) -or $selectedPort -lt 1 -or $selectedPort -gt 65535) { throw 'Enter a TCP port between 1 and 65535.' }
                    $Port = $selectedPort
                }
            }
            if (Get-Command Test-NetConnection -ErrorAction SilentlyContinue) {
                $result = Test-NetConnection -ComputerName $HostName -Port $Port -WarningAction SilentlyContinue -ErrorAction Stop
                Show-Rows @([pscustomobject]@{Host=$HostName; Port=$Port; RemoteAddress=$result.RemoteAddress;
                    SourceAddress=$result.SourceAddress; TcpSucceeded=$result.TcpTestSucceeded})
                if (-not $result.TcpTestSucceeded) { throw 'The TCP connection did not succeed. Check the host, port, service and firewall.' }
            } else {
                $client = New-Object System.Net.Sockets.TcpClient
                try {
                    $pending = $client.ConnectAsync($HostName.Trim('[',']'), $Port)
                    if (-not $pending.Wait(5000)) { throw 'TCP connection timed out after five seconds.' }
                    if (-not $client.Connected) { throw 'TCP connection was refused or unavailable.' }
                    Show-Rows @([pscustomobject]@{Host=$HostName; Port=$Port; RemoteAddress=$client.Client.RemoteEndPoint; TcpSucceeded=$true})
                } finally { $client.Dispose() }
            }
        }
        'dns' {
            if (-not (Select-Host)) { return }
            if (Get-Command Resolve-DnsName -ErrorAction SilentlyContinue) {
                $records = @(Resolve-DnsName -Name $HostName.Trim('[',']') -ErrorAction Stop)
                if ($records.Count -eq 0) { throw 'DNS returned no records.' }
                Show-Rows ($records | Select-Object Name,Type,IPAddress,NameHost,TTL)
            } else {
                Write-Host 'DnsClient module unavailable; showing addresses from the system DNS resolver.'
                $addresses = @([Net.Dns]::GetHostAddresses($HostName.Trim('[',']')))
                if ($addresses.Count -eq 0) { throw 'DNS returned no addresses.' }
                Show-Rows ($addresses | Select-Object @{n='Host';e={$HostName}},IPAddressToString,AddressFamily)
            }
        }
        'routes' {
            try {
                $configurations = @(Get-NetIPConfiguration -ErrorAction Stop)
                if ($configurations.Count -eq 0) { throw 'No network interface configuration was returned.' }
                Show-Rows ($configurations | ForEach-Object {[pscustomobject]@{
                    Interface=$_.InterfaceAlias; IPv4=($_.IPv4Address.IPAddress -join ', '); IPv6=($_.IPv6Address.IPAddress -join ', ');
                    Gateway=(@($_.IPv4DefaultGateway.NextHop) + @($_.IPv6DefaultGateway.NextHop) -join ', ')
                }})
                Show-Rows (Get-NetRoute -ErrorAction Stop | Where-Object {$_.DestinationPrefix -in @('0.0.0.0/0','::/0')} |
                    Select-Object InterfaceAlias,DestinationPrefix,NextHop,RouteMetric)
                Show-Rows (Get-DnsClientServerAddress -ErrorAction Stop | Where-Object {$_.ServerAddresses.Count -gt 0} |
                    Select-Object InterfaceAlias,AddressFamily,@{n='DNSServers';e={$_.ServerAddresses -join ', '}})
            } catch {
                Write-Warning ('Network cmdlets unavailable: ' + $_.Exception.Message + ' Using Windows network tools instead.')
                Run-Native (Require-Native 'ipconfig.exe') @('/all')
                Run-Native (Require-Native 'route.exe') @('print')
            }
        }
        'path' {
            $seen = @{}; $index = 0
            $rows = foreach ($entry in ([string]$env:PATH -split ';')) {
                $index++
                $expanded = [Environment]::ExpandEnvironmentVariables($entry.Trim().Trim('"'))
                $empty = [string]::IsNullOrWhiteSpace($expanded)
                $key = $expanded.TrimEnd('\','/').ToLowerInvariant()
                try { $exists = -not $empty -and (Test-Path -LiteralPath $expanded -PathType Container -ErrorAction Stop) }
                catch { $exists = 'unreadable' }
                $duplicate = $seen.ContainsKey($key)
                $seen[$key] = $true
                [pscustomobject]@{Index=$index; Entry=$(if ($empty) {'(empty entry: current directory)'} else {$entry}); Exists=$exists; Duplicate=$duplicate}
            }
            Show-Rows @($rows)
            Write-Host 'Only PATH was inspected. Empty entries and duplicate folders are shown without changing them.'
        }
        'disk' {
            $rows = @()
            foreach ($drive in [IO.DriveInfo]::GetDrives()) {
                try {
                    if (-not $drive.IsReady) { Write-Warning ('Volume not ready: ' + $drive.Name); continue }
                    $rows += [pscustomobject]@{Drive=$drive.Name; Label=$drive.VolumeLabel; Type=$drive.DriveType; Format=$drive.DriveFormat;
                        TotalGB=[Math]::Round($drive.TotalSize / 1GB,2); UsedGB=[Math]::Round(($drive.TotalSize-$drive.TotalFreeSpace) / 1GB,2);
                        FreeGB=[Math]::Round($drive.TotalFreeSpace / 1GB,2);
                        FreePercent=$(if ($drive.TotalSize -gt 0) {[Math]::Round(100*$drive.TotalFreeSpace/$drive.TotalSize,1)} else {$null})}
                } catch { Write-Warning ('Cannot read volume ' + $drive.Name + ': ' + $_.Exception.Message) }
            }
            if ($rows.Count -eq 0) { throw 'No readable volumes were found.' }
            Show-Rows $rows
        }
        'startup' {
            $rows = @(); $unreadable = 0
            foreach ($key in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Run','HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce',
                'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run','HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce',
                'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run')) {
                try {
                    if (-not (Test-Path -LiteralPath $key -ErrorAction Stop)) { continue }
                    $registry = Get-Item -LiteralPath $key -ErrorAction Stop
                    foreach ($name in $registry.GetValueNames()) { $rows += [pscustomobject]@{Name=$name; Location=$key} }
                } catch { $unreadable++; Write-Warning ('Cannot read startup location ' + $key + ': ' + $_.Exception.Message) }
            }
            foreach ($folder in @([Environment]::GetFolderPath('Startup'),[Environment]::GetFolderPath('CommonStartup'))) {
                if (-not $folder) { continue }
                try {
                    foreach ($file in Get-ChildItem -LiteralPath $folder -File -ErrorAction Stop) {
                        if ($file.Name -ne 'desktop.ini') { $rows += [pscustomobject]@{Name=$file.Name; Location=$folder} }
                    }
                } catch { $unreadable++; Write-Warning ('Cannot read startup folder ' + $folder + ': ' + $_.Exception.Message) }
            }
            if ($rows.Count -eq 0 -and $unreadable -gt 0) { throw 'Startup information could not be fully read. See access errors above.' }
            Show-Rows $rows
            Write-Host 'Entry names and locations only; command lines and their arguments are not displayed.'
        }
        'wsl' {
            $executable = Require-Native 'wsl.exe'
            Run-Native $executable @('--status')
            Run-Native $executable @('--list','--verbose')
        }
        'docker' {
            $executable = Require-Native 'docker.exe'
            Run-Native $executable @('ps','--all','--format','table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}')
            Run-Native $executable @('stats','--no-stream')
        }
        'longpaths' {
            $key = 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem'
            $value = (Get-ItemProperty -LiteralPath $key -ErrorAction Stop).LongPathsEnabled
            $status = if ($null -eq $value) {'Not configured'} elseif ($value -eq 1) {'Enabled'} elseif ($value -eq 0) {'Disabled'} else {'Unrecognized value: ' + $value}
            Write-Host ('Windows LongPathsEnabled: ' + $status)
            $git = Require-Native 'git.exe'
            if (-not $Project) { $Project = (Get-Location).Path }
            if (-not (Test-Path -LiteralPath $Project -PathType Container)) { throw ('Project folder does not exist: ' + $Project) }
            $result = Invoke-NativeCapture $git @('-C',$Project,'config','--show-origin','--get','core.longpaths')
            if ($result.exitCode -eq 1) { Write-Host 'Git core.longpaths: not configured for this project/user.' }
            elseif ($result.exitCode -eq 0) {
                Write-Host 'Git core.longpaths (effective value and source):'
                foreach ($line in $result.lines) { Write-Host $line }
            } else { throw ('Git configuration could not be read: ' + ($result.lines -join ' ')) }
            Write-Host 'Settings were read only. Application support for long paths can differ.'
        }
    }
    exit 0
} catch {
    Write-Host ('Diagnostics failed: ' + $_.Exception.Message) -ForegroundColor Red
    exit 2
}
