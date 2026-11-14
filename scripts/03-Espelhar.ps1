<#
.SYNOPSIS
  Abre o espelhamento + controle por teclado/mouse com scrcpy.
.DESCRIPTION
  Usa o MESMO adb do projeto (variavel ADB) para evitar o conflito
  "adb server version doesn't match" entre o adb do scrcpy e o do Platform Tools.
  Conteudo com DRM (Netflix, Prime etc.) costuma aparecer PRETO no espelhamento: e esperado.
  Atalhos uteis do scrcpy: Alt+H = Home | Alt+B ou botao direito = Voltar | Alt+S = Recentes
                           Alt+Up/Down = volume | Alt+O = desligar tela da TV (mantem espelhando)
.EXAMPLE
  .\03-Espelhar.ps1
  .\03-Espelhar.ps1 -SomenteControle   # sem video (mais leve), so teclado/mouse
#>
param([switch]$SomenteControle, [switch]$Gravar)
. "$PSScriptRoot\Comum.ps1"
$scrcpy = Find-XtmTool -Name scrcpy
if (-not $scrcpy) { throw 'scrcpy nao encontrado. Rode 00-Preparar-Windows.ps1.' }
$serial = Get-XtmSerial
if ((Get-XtmDeviceState -Serial $serial) -ne 'device') { & "$PSScriptRoot\02-Conectar.ps1" | Out-Host }
$env:ADB = Get-XtmAdb
$cfg = Get-XtmConfig
$argsList = @('-s', $serial, '--window-title=Mi TV Stick') + @($cfg.scrcpy_args)
if ($SomenteControle) { $argsList += '--no-video'; $argsList += '--no-audio' }
if ($Gravar) { $argsList += ('--record={0}' -f (Join-Path $XtmReports ('gravacao-{0}.mkv' -f (Get-Date -Format 'yyyyMMdd-HHmmss')))) }
Write-XtmLog ("scrcpy {0}" -f ($argsList -join ' '))
& $scrcpy @argsList
Write-XtmLog "scrcpy finalizou com codigo $LASTEXITCODE"
