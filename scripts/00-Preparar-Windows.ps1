<#
.SYNOPSIS
  Identifica o ambiente Windows e instala ADB (Platform Tools), scrcpy e Python via winget.
.DESCRIPTION
  - Mostra a versao do Windows, PowerShell, winget e a configuracao de rede (IPv4, gateway, DNS).
  - Instala somente pacotes oficiais do winget: Google.PlatformTools, Genymobile.scrcpy, Python.Python.3.12.
  - NAO altera Defender, firewall, UAC nem a politica de execucao do sistema.
  - Copia (opcionalmente) o projeto para %USERPROFILE%\Documents\Xiaomi-TV-Manager.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\00-Preparar-Windows.ps1
.EXAMPLE
  .\scripts\00-Preparar-Windows.ps1 -SomenteVerificar
#>
param([switch]$SomenteVerificar, [switch]$SemCopiarProjeto)
. "$PSScriptRoot\Comum.ps1"

$report = New-Object System.Collections.Generic.List[string]
function Add-R([string]$t) { $report.Add($t); Write-Host $t }

Add-R '# Ambiente Windows'
Add-R ('Data: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
try {
    $os = Get-CimInstance Win32_OperatingSystem
    Add-R ('Windows: {0} | versao {1} | build {2} | {3}' -f $os.Caption, $os.Version, $os.BuildNumber, $os.OSArchitecture)
    $dv = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' -ErrorAction SilentlyContinue).DisplayVersion
    if ($dv) { Add-R ('Release: {0}' -f $dv) }
} catch { Add-R ('Windows: {0}' -f [Environment]::OSVersion.VersionString) }
Add-R ('PowerShell: {0} ({1})' -f $PSVersionTable.PSVersion, $PSVersionTable.PSEdition)

$winget = Get-Command winget.exe -ErrorAction SilentlyContinue
if ($winget) { Add-R ('winget: {0}' -f ((& winget --version) -join '')) } else { Add-R 'winget: NAO encontrado (instale o "App Installer" pela Microsoft Store).' }

Add-R ''
Add-R '# Rede'
try {
    Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } | ForEach-Object {
        Add-R ('Interface: {0} ({1})' -f $_.InterfaceAlias, $_.NetAdapter.InterfaceDescription)
        Add-R ('  IPv4: {0}/{1}' -f $_.IPv4Address.IPAddress, $_.IPv4Address.PrefixLength)
        Add-R ('  Gateway: {0}' -f $_.IPv4DefaultGateway.NextHop)
        Add-R ('  DNS: {0}' -f (($_.DNSServer | Where-Object AddressFamily -eq 2).ServerAddresses -join ', '))
        $perfilRede = Get-NetConnectionProfile -InterfaceAlias $_.InterfaceAlias -ErrorAction SilentlyContinue
        if ($perfilRede) { Add-R ('  Perfil de rede: {0}' -f $perfilRede.NetworkCategory) }
    }
} catch { Add-R ('Falha ao ler rede: {0}' -f $_.Exception.Message) }

Add-R ''
Add-R '# Ferramentas'
$tools = @(
    @{ Nome = 'ADB (Android Platform Tools)'; Id = 'Google.PlatformTools'; Teste = { Find-XtmTool -Name adb } },
    @{ Nome = 'scrcpy';                        Id = 'Genymobile.scrcpy';    Teste = { Find-XtmTool -Name scrcpy } },
    @{ Nome = 'Python 3 (com Tkinter, testado)'; Id = 'Python.Python.3.12'; Teste = { Find-XtmPython } }
)
foreach ($t in $tools) {
    $path = & $t.Teste
    if ($path) { Add-R ('[OK]   {0}: {1}' -f $t.Nome, $path); continue }
    Add-R ('[FALTA] {0}' -f $t.Nome)
    if ($SomenteVerificar) { continue }
    if (-not $winget) { Write-XtmLog "Sem winget: instale $($t.Nome) manualmente (veja README)." WARN; continue }
    Write-XtmLog "Instalando $($t.Id) via winget (fonte oficial)..." INFO
    $prevEap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    & winget install --id $t.Id --exact --source winget --accept-package-agreements --accept-source-agreements --silent
    $ErrorActionPreference = $prevEap
    Update-XtmPath
    $path = & $t.Teste
    if ($path) { Add-R ('[OK]   {0} instalado: {1}' -f $t.Nome, $path) } else { Add-R ('[ERRO] {0}: instalacao nao confirmada. Feche e reabra o PowerShell e rode novamente.' -f $t.Nome) }
}

# Versoes
$adb = Find-XtmTool -Name adb
if ($adb) { Add-R ('adb version: {0}' -f ((& $adb version | Select-Object -First 2) -join ' | ')) }
# Comandos externos rodam com 'Continue': no Windows PowerShell 5.1, texto em stderr + 2>&1 com 'Stop' aborta o script.
$ErrorActionPreference = 'Continue'
$scrcpy = Find-XtmTool -Name scrcpy
if ($scrcpy) { Add-R ('scrcpy: {0}' -f ((& $scrcpy --version 2>&1 | Select-Object -First 1 | ForEach-Object { "$_" }) -join '')) }

# Python que realmente funciona (ignora instalacoes quebradas, ex.: em drive removido)
$pyw = Find-XtmPython
if ($pyw) { Save-XtmPython -PythonW $pyw; Add-R ('Python do painel: {0}' -f $pyw) }
else { Add-R '[ERRO] Nenhum Python funcional com Tkinter foi encontrado.' }

# Grava caminhos encontrados na configuracao
$cfg = Get-XtmConfig
if ($adb)    { $cfg.adb_path = $adb }
if ($scrcpy) { $cfg.scrcpy_path = $scrcpy }
Save-XtmConfig $cfg

# Pasta do projeto
$target = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Xiaomi-TV-Manager'
if (-not $SemCopiarProjeto -and -not $SomenteVerificar -and ($XtmRoot -ne $target)) {
    if (-not (Test-Path $target)) {
        Copy-Item -Path $XtmRoot -Destination $target -Recurse
        Add-R ('Projeto copiado para {0}' -f $target)
    } else { Add-R ('Pasta {0} ja existe; nada foi sobrescrito.' -f $target) }
}

$out = Join-Path $XtmReports ('ambiente-windows-{0}.md' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
$report | Set-Content -Path $out -Encoding UTF8
Write-XtmLog "Relatorio do ambiente salvo em $out" OK
