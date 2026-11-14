<#
.SYNOPSIS
  Lista e abre aplicativos no Mi Stick.
.EXAMPLE
  .\07-Abrir-App.ps1 -Listar
  .\07-Abrir-App.ps1 -App netflix
  .\07-Abrir-App.ps1 -Pacote com.google.android.youtube.tv
#>
param([switch]$Listar, [string]$App, [string]$Pacote)
. "$PSScriptRoot\Comum.ps1"
$serial = Get-XtmSerial
$atalhos = [ordered]@{
    netflix = 'com.netflix.ninja'; youtube = 'com.google.android.youtube.tv'; prime = 'com.amazon.amazonvideo.livingroom'
    disney = 'com.disney.disneyplus'; max = 'com.wbd.stream'; globoplay = 'com.globo.globotv'; spotify = 'com.spotify.tv.android'
    playstore = 'com.android.vending'; configuracoes = 'com.android.tv.settings'
}
if ($Listar) {
    Write-Host 'Atalhos:' -ForegroundColor Cyan; $atalhos.GetEnumerator() | ForEach-Object { '  {0,-14} {1}' -f $_.Key, $_.Value }
    Write-Host 'Apps com icone na tela inicial (LEANBACK_LAUNCHER):' -ForegroundColor Cyan
    $r = Invoke-XtmShell -Serial $serial -Command 'cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.LEANBACK_LAUNCHER'
    ($r -split "`n") | Where-Object { $_ -match '/' } | ForEach-Object { '  ' + ($_.Trim() -split '/')[0] } | Sort-Object -Unique
    exit 0
}
if ($App) { $k = $App.ToLowerInvariant(); if (-not $atalhos.Contains($k)) { throw "Atalho desconhecido: $App" }; $Pacote = $atalhos[$k] }
if (-not $Pacote) { throw 'Informe -App, -Pacote ou -Listar.' }
$r = Invoke-XtmShell -Serial $serial -Command "monkey -p $Pacote -c android.intent.category.LEANBACK_LAUNCHER 1"
if ($r -match 'No activities found|aborted') { $r = Invoke-XtmShell -Serial $serial -Command "monkey -p $Pacote -c android.intent.category.LAUNCHER 1" }
if ($r -match 'No activities found|aborted') { Write-XtmLog "Nao foi possivel abrir $Pacote (instalado?)." ERRO; Write-Host $r; exit 1 }
Write-XtmLog "Aberto: $Pacote" OK
