<#
.SYNOPSIS
  Vigia a conexao ADB e reconecta quando ela cair. Ctrl+C para parar.
.EXAMPLE
  .\06-Reconectar.ps1 -IntervaloSeg 15
#>
param([int]$IntervaloSeg = 15, [switch]$UmaVez)
. "$PSScriptRoot\Comum.ps1"
$serial = Get-XtmSerial
$ip = ($serial -split ':')[0]; $porta = [int]($serial -split ':')[1]
$falhas = 0
do {
    $st = Get-XtmDeviceState -Serial $serial
    if ($st -eq 'device') {
        if ($falhas -gt 0) { Write-XtmLog "Conexao restabelecida com $serial" OK }
        elseif ($UmaVez) { Write-XtmLog "Conectado: $serial" OK }
        $falhas = 0
    } else {
        $falhas++
        Write-XtmLog "Estado '$st' (tentativa $falhas). Reconectando..." WARN
        if ($st -eq 'offline') { Invoke-XtmAdb disconnect $serial | Out-Null }
        if (Test-XtmTcpPort -Ip $ip -Port $porta -TimeoutMs 1500) {
            Write-Host (Invoke-XtmAdb connect $serial)
            if ((Get-XtmDeviceState -Serial $serial) -eq 'unauthorized') { Write-XtmLog 'Aguardando autorizacao na TV.' WARN }
        } else {
            Write-XtmLog "Porta $porta fechada/inalcancavel (TV desligada, em suspensao profunda ou IP mudou)." WARN
        }
    }
    if ($UmaVez) { break }
    # Espera progressiva ate 2 minutos para nao poluir a rede quando a TV esta desligada.
    Start-Sleep -Seconds ([math]::Min(120, $IntervaloSeg * [math]::Max(1, [math]::Min($falhas, 8))))
} while ($true)
