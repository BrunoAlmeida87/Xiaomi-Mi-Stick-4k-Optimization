<#
.SYNOPSIS
  Coleta diagnostico completo e SOMENTE LEITURA do Mi Stick (nenhuma configuracao e alterada).
.DESCRIPTION
  Salva cada comando em reports\diagnostico-<data>\NN-nome.txt e gera resumo.md.
  Use antes e depois de qualquer otimizacao para comparar.
#>
param([int]$LinhasLog = 3000)
. "$PSScriptRoot\Comum.ps1"
$serial = Get-XtmSerial
if ((Get-XtmDeviceState -Serial $serial) -ne 'device') { throw "Dispositivo $serial nao esta conectado/autorizado. Rode 02-Conectar.ps1." }

$dir = Join-Path $XtmReports ('diagnostico-{0}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $dir | Out-Null

$cmds = [ordered]@{
    '01-getprop'               = 'getprop'
    '02-meminfo'               = 'cat /proc/meminfo'
    '03-dumpsys-meminfo'       = 'dumpsys meminfo'
    '04-armazenamento'         = 'df -h; echo; df'
    '05-cpuinfo'               = 'cat /proc/cpuinfo'
    '06-top'                   = 'top -b -n 1 -m 30'
    '07-dumpsys-cpuinfo'       = 'dumpsys cpuinfo'
    '08-uptime-load'           = 'uptime; cat /proc/loadavg'
    '09-servicos-execucao'     = 'dumpsys activity services'
    '10-processos-lru'         = 'dumpsys activity lru'
    '11-pacotes-sistema'       = 'pm list packages -s -f'
    '12-pacotes-terceiros'     = 'pm list packages -3 -f'
    '13-pacotes-desativados'   = 'pm list packages -d'
    '14-animacoes'             = 'echo window=$(settings get global window_animation_scale); echo transition=$(settings get global transition_animation_scale); echo animator=$(settings get global animator_duration_scale)'
    '15-usagestats'            = 'dumpsys usagestats'
    '16-logcat-erros'          = "logcat -d -v time -t $LinhasLog *:E"
    '17-logcat-crash'          = 'logcat -d -v time -b crash'
    '18-conectividade'         = 'dumpsys connectivity'
    '19-wifi'                  = 'dumpsys wifi'
    '20-bluetooth'             = 'dumpsys bluetooth_manager'
    '21-dispositivos-entrada'  = 'dumpsys input'
    '22-logcat-bluetooth'      = "logcat -d -v time -t $LinhasLog | grep -iE 'bluetooth|bt_|hidhost|hid_|a2dp|gatt|bta_|btif|remote'"
    '23-termico'               = 'dumpsys thermalservice'
    '24-hdmi-cec'              = 'dumpsys hdmi_control'
    '25-settings-global'       = 'settings list global'
    '26-settings-secure'       = 'settings list secure'
    '27-dispositivos-ip'       = 'ip addr; ip route'
    '28-diskstats'             = 'dumpsys diskstats'
}
$i = 0
foreach ($n in $cmds.Keys) {
    $i++
    Write-Progress -Activity 'Diagnostico' -Status $n -PercentComplete ($i * 100 / $cmds.Count)
    $txt = Invoke-XtmShell -Serial $serial -Command $cmds[$n]
    Set-Content -Path (Join-Path $dir "$n.txt") -Value ("# adb shell {0}`n{1}" -f $cmds[$n], $txt) -Encoding UTF8
}
Write-Progress -Activity 'Diagnostico' -Completed

# Resumo
function P($k) { (Invoke-XtmShell -Serial $serial -Command "getprop $k").Trim() }
$mem = Get-Content (Join-Path $dir '02-meminfo.txt')
function M($k) { $l = $mem | Where-Object { $_ -match "^$k\s*:" } | Select-Object -First 1; if ($l -match '(\d+)\s*kB') { [math]::Round([int64]$Matches[1] / 1024) } else { 'n/d' } }
$df = Invoke-XtmShell -Serial $serial -Command 'df -h /data'
$anim = Get-Content (Join-Path $dir '14-animacoes.txt') | Select-Object -Skip 1
$load = (Invoke-XtmShell -Serial $serial -Command 'cat /proc/loadavg').Trim()

$resumo = @"
# Resumo do diagnostico - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

| Item | Valor |
|---|---|
| Fabricante / Modelo | $(P ro.product.manufacturer) / $(P ro.product.model) ($(P ro.product.device)) |
| Android | $(P ro.build.version.release) (SDK $(P ro.build.version.sdk)) |
| Firmware | $(P ro.build.display.id) |
| Patch de seguranca | $(P ro.build.version.security_patch) |
| Plataforma | $(P ro.board.platform) / $(P ro.hardware) |
| RAM total (MB) | $(M MemTotal) |
| RAM disponivel (MB) | $(M MemAvailable) |
| Swap/ZRAM total / livre (MB) | $(M SwapTotal) / $(M SwapFree) |
| Load average | $load |
| Animacoes | $($anim -join ' ; ') |

## Armazenamento /data
``````
$df
``````

Arquivos brutos nesta pasta. Observacao: uso alto de RAM no Android e normal (cache de apps);
avalie MemAvailable, swap ativo e travamentos, nao apenas "memoria usada".
"@
$resumo | Set-Content -Path (Join-Path $dir 'resumo.md') -Encoding UTF8
Write-XtmLog "Diagnostico salvo em $dir" OK
Get-Content (Join-Path $dir 'resumo.md') | Write-Host
