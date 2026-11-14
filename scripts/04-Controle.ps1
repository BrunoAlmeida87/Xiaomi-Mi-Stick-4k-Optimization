<#
.SYNOPSIS
  Controle remoto pelo teclado no proprio PowerShell (sem espelhamento) ou envio de teclas avulsas.
.EXAMPLE
  .\04-Controle.ps1                 # modo interativo
  .\04-Controle.ps1 -Tecla HOME     # envia uma tecla e sai
  .\04-Controle.ps1 -Tecla UP,UP,OK # sequencia
  .\04-Controle.ps1 -Texto "stranger things"
#>
param([string[]]$Tecla, [string]$Texto)
. "$PSScriptRoot\Comum.ps1"
$serial = Get-XtmSerial
if ((Get-XtmDeviceState -Serial $serial) -ne 'device') { & "$PSScriptRoot\02-Conectar.ps1" | Out-Host }

if ($Texto) {
    # input text: espaco vira %s; caracteres especiais do shell sao escapados.
    $t = ($Texto -replace '([\\"''`$&|;<>()*?!#~])', '\$1') -replace ' ', '%s'
    Invoke-XtmShell -Serial $serial -Command "input text `"$t`"" | Out-Null
    exit 0
}
if ($Tecla) { foreach ($k in @($Tecla | ForEach-Object { $_ -split ',' } | Where-Object { $_ })) { Send-XtmKey -Key $k -Serial $serial }; exit 0 }

$mapa = @{
    'UpArrow' = 'UP'; 'DownArrow' = 'DOWN'; 'LeftArrow' = 'LEFT'; 'RightArrow' = 'RIGHT'
    'Enter' = 'OK'; 'Backspace' = 'BACK'; 'Escape' = 'BACK'; 'H' = 'HOME'; 'M' = 'MENU'
    'Spacebar' = 'PLAYPAUSE'; 'N' = 'NEXT'; 'P' = 'PREV'; 'F' = 'FF'; 'R' = 'REW'
    'OemPlus' = 'VOLUP'; 'Add' = 'VOLUP'; 'OemMinus' = 'VOLDOWN'; 'Subtract' = 'VOLDOWN'; 'X' = 'MUTE'
    'S' = 'SETTINGS'; 'L' = 'SLEEP'; 'W' = 'WAKEUP'; 'A' = 'ASSIST'
}
Write-Host 'Controle remoto - Mi TV Stick' -ForegroundColor Cyan
Write-Host 'Setas=direcional | Enter=OK | Backspace/Esc=Voltar | H=Home | M=Menu | Espaco=Play/Pause'
Write-Host 'N/P=proxima/anterior | F/R=avancar/voltar | +/-=volume | X=mudo | S=Configuracoes | L/W=dormir/acordar | A=Assistente | Q=sair'
while ($true) {
    $k = [Console]::ReadKey($true)
    $nome = $k.Key.ToString()
    if ($nome -eq 'Q') { break }
    if ($mapa.ContainsKey($nome)) {
        try { Send-XtmKey -Key $mapa[$nome] -Serial $serial; Write-Host ("-> {0}" -f $mapa[$nome]) }
        catch { Write-XtmLog $_.Exception.Message ERRO }
    }
}
