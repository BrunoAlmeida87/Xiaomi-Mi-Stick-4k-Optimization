<#
.SYNOPSIS
  Diagnostico SOMENTE LEITURA do Bluetooth e do controle remoto. Nao altera pareamentos.
#>
param([int]$LinhasLog = 5000)
. "$PSScriptRoot\Comum.ps1"
$serial = Get-XtmSerial
$bt = Invoke-XtmShell -Serial $serial -Command 'dumpsys bluetooth_manager'
$out = Join-Path $XtmReports ('bluetooth-{0}.txt' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))

$estado = ($bt -split "`n" | Where-Object { $_ -match '^\s*(enabled|state|name|address):' } | Select-Object -First 6) -join "`n"
$bonded = ($bt -split "`n" | Where-Object { $_ -match 'Bonded devices' -or $_ -match '^\s+[0-9A-F]{2}(:[0-9A-F]{2}){5}' -or $_ -match 'XX:XX:XX:XX' } | Select-Object -First 20) -join "`n"
$entrada = Invoke-XtmShell -Serial $serial -Command "dumpsys input | grep -iE 'Device [0-9]+:|Name:|Sources:|Bluetooth|Descriptor:'"
$log = Invoke-XtmShell -Serial $serial -Command "logcat -d -v time -t $LinhasLog | grep -iE 'disconnect|link.?loss|connection.?timeout|hci.*(err|timeout)|hidhost|bta_hh|bond|pair|rssi|supervision' "

$eventos = @($log -split "`n" | Where-Object { $_.Trim() })
$descon = @($eventos | Where-Object { $_ -match 'disconnect|link.?loss|supervision|timeout' })

$txt = @"
=== ESTADO ===
$estado

=== DISPOSITIVOS PAREADOS (trecho) ===
$bonded

=== DISPOSITIVOS DE ENTRADA (o controle aparece aqui quando conectado) ===
$entrada

=== EVENTOS RELEVANTES NO LOGCAT (buffer atual: $($eventos.Count) linhas; possiveis desconexoes/timeouts: $($descon.Count)) ===
$log

=== DUMPSYS COMPLETO ===
$bt
"@
$txt | Set-Content -Path $out -Encoding UTF8
Write-Host $estado
Write-Host ''
Write-Host "Eventos de desconexao/timeout no buffer de log atual: $($descon.Count)"
Write-Host 'Obs.: o logcat guarda apenas o periodo recente (horas, nao dias). Rode logo apos uma falha do controle.'
Write-XtmLog "Relatorio Bluetooth: $out" OK
