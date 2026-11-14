<#
.SYNOPSIS
  Conecta ao Mi TV Stick via ADB pela rede (TCP/IP 5555 ou pareamento de depuracao sem fio).
.EXAMPLE
  .\02-Conectar.ps1 -Ip 192.168.0.50
.EXAMPLE
  # Depuracao sem fio (Android 11+): use o IP:porta e o codigo da tela "Parear com codigo"
  .\02-Conectar.ps1 -Parear -EnderecoPareamento 192.168.0.50:37123 -Codigo 123456 -Ip 192.168.0.50 -Porta 41235
.EXAMPLE
  .\02-Conectar.ps1 -Desconectar
#>
param(
    [string]$Ip, [int]$Porta = 0,
    [switch]$Parear, [string]$EnderecoPareamento, [string]$Codigo,
    [switch]$Desconectar, [int]$EsperaAutorizacaoSeg = 60
)
. "$PSScriptRoot\Comum.ps1"
$cfg = Get-XtmConfig
if (-not $Ip) { $Ip = $cfg.ip }
if ($Porta -eq 0) { $Porta = [int]$cfg.port }
if (-not $Ip) { $Ip = Read-Host 'IP do Mi Stick (Configuracoes > Preferencias do dispositivo > Sobre > Status)' }
if ($Ip -notmatch '^\d{1,3}(\.\d{1,3}){3}$') { throw "IP invalido: $Ip" }
$serial = '{0}:{1}' -f $Ip, $Porta

if ($Desconectar) { Write-Host (Invoke-XtmAdb disconnect $serial); exit 0 }

Invoke-XtmAdb start-server | Out-Null

if ($Parear) {
    if (-not $EnderecoPareamento) { $EnderecoPareamento = Read-Host 'IP:porta exibidos em "Parear dispositivo com codigo"' }
    if (-not $Codigo) { $Codigo = Read-Host 'Codigo de pareamento de 6 digitos' }
    Write-XtmLog "Pareando com $EnderecoPareamento ..."
    $r = Invoke-XtmAdb pair $EnderecoPareamento $Codigo
    Write-Host $r
    if ($r -notmatch 'Successfully paired') { Write-XtmLog 'Pareamento nao confirmado.' ERRO; exit 2 }
    Write-XtmLog 'Pareado. Use agora a porta de "Depuracao sem fio" (diferente da porta de pareamento).' OK
}

Write-XtmLog "Testando porta TCP $Porta em $Ip ..."
if (-not (Test-XtmTcpPort -Ip $Ip -Port $Porta -TimeoutMs 1500)) {
    Write-XtmLog "A porta $Porta nao respondeu em $Ip." WARN
    Write-Host 'Possiveis causas: depuracao ADB desativada, IP errado, TV em outra rede/VLAN, ou o firmware usa depuracao sem fio com outra porta.'
    Write-Host 'Veja docs\MODO-DESENVOLVEDOR.md. Mesmo assim vou tentar adb connect.'
}

Write-XtmLog "adb connect $serial"
$r = Invoke-XtmAdb connect $serial
Write-Host $r
if ($r -match 'failed|cannot|refused|unable') { Write-XtmLog 'Conexao recusada.' ERRO; exit 3 }

Write-Host ''
Write-Host '>>> Se aparecer na TV a janela "Permitir depuracao USB?", marque "Sempre permitir deste computador" e escolha OK. <<<' -ForegroundColor Cyan
$limite = (Get-Date).AddSeconds($EsperaAutorizacaoSeg)
do {
    $st = Get-XtmDeviceState -Serial $serial
    if ($st -eq 'device') { break }
    if ($st -eq 'unauthorized') { Write-Host -NoNewline '.'; Start-Sleep 2; continue }
    if ($st -eq 'offline') { Invoke-XtmAdb reconnect offline | Out-Null; Start-Sleep 2; Invoke-XtmAdb connect $serial | Out-Null }
    Start-Sleep 2
} while ((Get-Date) -lt $limite)
Write-Host ''

if ($st -ne 'device') { Write-XtmLog "Estado final: $st. Autorize na TV e rode o script novamente." ERRO; exit 4 }

$cfg.ip = $Ip; $cfg.port = $Porta; Save-XtmConfig $cfg
Write-XtmLog "Conectado e autorizado: $serial" OK
Write-Host (Invoke-XtmAdb devices -l)
$props = 'ro.product.manufacturer','ro.product.model','ro.product.device','ro.build.version.release','ro.build.version.sdk','ro.build.display.id','ro.build.version.security_patch','ro.product.cpu.abi'
foreach ($p in $props) { '{0,-34} {1}' -f $p, (Invoke-XtmShell -Serial $serial -Command "getprop $p").Trim() | Write-Host }
