# Comum.ps1 - funcoes compartilhadas pelos scripts do Xiaomi TV Manager.
# Carregue com:  . "$PSScriptRoot\Comum.ps1"
# Compativel com Windows PowerShell 5.1 e PowerShell 7+.

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$Global:XtmRoot    = Split-Path -Parent $PSScriptRoot
$Global:XtmConfig  = Join-Path $XtmRoot 'config.json'
$Global:XtmLogDir  = Join-Path $XtmRoot 'logs'
$Global:XtmReports = Join-Path $XtmRoot 'reports'
foreach ($d in @($XtmLogDir, $XtmReports)) { if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null } }

function Write-XtmLog {
    param([Parameter(Mandatory)][string]$Message, [ValidateSet('INFO','WARN','ERRO','OK')][string]$Level = 'INFO')
    $line = '{0} [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    $color = @{ INFO = 'Gray'; WARN = 'Yellow'; ERRO = 'Red'; OK = 'Green' }[$Level]
    Write-Host $line -ForegroundColor $color
    Add-Content -Path (Join-Path $XtmLogDir ('xtm-{0}.log' -f (Get-Date -Format 'yyyyMMdd'))) -Value $line -Encoding UTF8
}

function Get-XtmConfig {
    if (Test-Path $XtmConfig) { return (Get-Content $XtmConfig -Raw -Encoding UTF8 | ConvertFrom-Json) }
    return [pscustomobject]@{ ip = ''; port = 5555; auto_reconnect = $true; adb_path = ''; scrcpy_path = ''; scrcpy_args = @('--max-size=1280','--max-fps=30','--video-bit-rate=4M') }
}

function Save-XtmConfig { param([Parameter(Mandatory)]$Config)
    $Config | ConvertTo-Json -Depth 5 | Set-Content -Path $XtmConfig -Encoding UTF8
}

function Update-XtmPath {
    # Recarrega o PATH (Maquina + Usuario) apos instalacoes via winget, sem reiniciar o terminal.
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
}

function Find-XtmTool {
    param([Parameter(Mandatory)][ValidateSet('adb','scrcpy')][string]$Name)
    $cfg = Get-XtmConfig
    $key = '{0}_path' -f $Name
    $configured = $null
    if ($cfg.PSObject.Properties.Name -contains $key) { $configured = $cfg.$key }
    if ($configured -and (Test-Path $configured)) { return (Resolve-Path $configured).Path }

    $cmd = Get-Command "$Name.exe" -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $candidates = @()
    $wingetPkgs = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    if ($Name -eq 'adb') {
        $candidates += Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
        if (Test-Path $wingetPkgs) { $candidates += Get-ChildItem $wingetPkgs -Filter 'adb.exe' -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match 'PlatformTools' } | ForEach-Object FullName }
    } else {
        if (Test-Path $wingetPkgs) { $candidates += Get-ChildItem $wingetPkgs -Filter 'scrcpy.exe' -Recurse -ErrorAction SilentlyContinue | ForEach-Object FullName }
    }
    foreach ($c in $candidates) { if ($c -and (Test-Path $c)) { return $c } }
    return $null
}

function Get-XtmAdb {
    $adb = Find-XtmTool -Name adb
    if (-not $adb) { throw 'ADB nao encontrado. Execute scripts\00-Preparar-Windows.ps1 primeiro.' }
    return $adb
}

function Get-XtmSerial {
    param([string]$Ip, [int]$Port = 0)
    $cfg = Get-XtmConfig
    if (-not $Ip) { $Ip = $cfg.ip }
    if ($Port -eq 0) { $Port = [int]$cfg.port }
    if (-not $Ip) { throw 'IP do Mi Stick nao configurado. Rode scripts\01-Descobrir-MiStick.ps1 ou scripts\02-Conectar.ps1 -Ip <endereco>.' }
    return '{0}:{1}' -f $Ip, $Port
}

function Invoke-XtmAdb {
    # Executa adb e devolve a saida como texto (stdout+stderr). Nao lanca excecao por exit code.
    param([Parameter(Mandatory, ValueFromRemainingArguments)][string[]]$Arguments)
    $adb = Get-XtmAdb
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { $out = & $adb @Arguments 2>&1 | ForEach-Object { "$_" } } finally { $ErrorActionPreference = $prev }
    return ($out -join "`n")
}

function Invoke-XtmShell {
    # adb -s <serial> shell <comando>
    param([Parameter(Mandatory)][string]$Command, [string]$Serial)
    if (-not $Serial) { $Serial = Get-XtmSerial }
    return Invoke-XtmAdb -s $Serial shell $Command
}

function Get-XtmDeviceState {
    param([string]$Serial)
    if (-not $Serial) { $Serial = Get-XtmSerial }
    $s = (Invoke-XtmAdb -s $Serial get-state).Trim()
    if ($s -match '^(device|offline|unauthorized|bootloader|recovery)$') { return $s }
    return 'desconectado'
}

function Test-XtmTcpPort {
    param([Parameter(Mandatory)][string]$Ip, [int]$Port = 5555, [int]$TimeoutMs = 400)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync($Ip, $Port)
        if ($task.Wait($TimeoutMs)) { return $client.Connected }
        return $false
    } catch { return $false } finally { $client.Dispose() }
}

# Mapa de teclas Android (KeyEvent) usado pelos scripts de controle.
$Global:XtmKeys = [ordered]@{
    UP = 19; DOWN = 20; LEFT = 21; RIGHT = 22; OK = 23; ENTER = 66
    BACK = 4; HOME = 3; MENU = 82; RECENTES = 187; SETTINGS = 176
    PLAYPAUSE = 85; PLAY = 126; PAUSE = 127; STOP = 86; NEXT = 87; PREV = 88; FF = 90; REW = 89
    VOLUP = 24; VOLDOWN = 25; MUTE = 164
    POWER = 26; SLEEP = 223; WAKEUP = 224; SEARCH = 84; ASSIST = 231
}

function Send-XtmKey {
    param([Parameter(Mandatory)][string]$Key, [string]$Serial)
    $k = $Key.ToUpperInvariant()
    if ($XtmKeys.Contains($k)) { $code = $XtmKeys[$k] }
    elseif ($k -match '^\d+$') { $code = [int]$k }
    else { throw "Tecla desconhecida: $Key. Validas: $($XtmKeys.Keys -join ', ')" }
    Invoke-XtmShell -Command "input keyevent $code" -Serial $Serial | Out-Null
}

# ---------------- Python ----------------
function Test-XtmPythonCandidate {
    # Retorna $true se o executavel existe, roda de verdade, e tem Python >= 3.8 com Tkinter.
    param([string]$Exe)
    if (-not $Exe -or -not (Test-Path -LiteralPath $Exe)) { return $false }
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try {
        $out = & $Exe -c "import sys, tkinter; print('XTM' + ('-OK' if sys.version_info >= (3, 8) else '-OLD'))" 2>&1 | ForEach-Object { "$_" }
        return (($out -join ' ') -match 'XTM-OK')
    } catch { return $false } finally { $ErrorActionPreference = $prev }
}

function Get-XtmPythonCandidates {
    $c = New-Object System.Collections.Generic.List[string]
    $cfg = Get-XtmConfig
    if ($cfg.PSObject.Properties.Name -contains 'python_path' -and $cfg.python_path) {
        $c.Add(($cfg.python_path -replace 'pythonw\.exe$', 'python.exe'))
    }
    foreach ($base in @((Join-Path "$env:LOCALAPPDATA" 'Programs\Python'), "$env:ProgramFiles", "${env:ProgramFiles(x86)}")) {
        if ($base -and (Test-Path $base)) {
            Get-ChildItem -Path $base -Directory -Filter 'Python3*' -ErrorAction SilentlyContinue |
                Sort-Object { [int](($_.Name -replace '\D', '') + '0') } -Descending |
                ForEach-Object { $c.Add((Join-Path $_.FullName 'python.exe')) }
        }
    }
    # Caminhos registrados no Python Launcher (py -0p). Entradas quebradas (ex.: drive removido) sao descartadas no teste.
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        try { $lista = & $py.Source -0p 2>&1 | ForEach-Object { "$_" } } catch { $lista = @() } finally { $ErrorActionPreference = $prev }
        foreach ($l in $lista) { if ($l -match '([A-Za-z]:\\.+?\.exe)\s*$') { $c.Add(($Matches[1] -replace 'pythonw\.exe$', 'python.exe')) } }
    }
    Get-Command python.exe -All -ErrorAction SilentlyContinue | Where-Object { $_.Source -notmatch 'WindowsApps' } | ForEach-Object { $c.Add($_.Source) }
    return @($c | Select-Object -Unique)
}

function Find-XtmPython {
    # Devolve o pythonw.exe (sem janela) de um Python que FUNCIONA, ou $null.
    foreach ($exe in Get-XtmPythonCandidates) {
        if (Test-XtmPythonCandidate $exe) {
            $w = Join-Path (Split-Path -Parent $exe) 'pythonw.exe'
            if (Test-Path -LiteralPath $w) { return $w }
            return $exe
        }
    }
    return $null
}

function Save-XtmPython {
    # Grava o Python escolhido em config.json e em data\python.txt (lido pelo Iniciar-XiaomiTVManager.bat).
    param([Parameter(Mandatory)][string]$PythonW)
    $cfg = Get-XtmConfig
    if ($cfg.PSObject.Properties.Name -contains 'python_path') { $cfg.python_path = $PythonW }
    else { $cfg | Add-Member -NotePropertyName python_path -NotePropertyValue $PythonW }
    Save-XtmConfig $cfg
    $dataDir = Join-Path $XtmRoot 'data'
    if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir | Out-Null }
    [IO.File]::WriteAllText((Join-Path $dataDir 'python.txt'), $PythonW, (New-Object System.Text.UTF8Encoding($false)))
}
