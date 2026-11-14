<#
.SYNOPSIS
  Instalacao completa em um passo (chamado pelo INSTALAR.bat):
  1) desbloqueia os arquivos baixados  2) copia o projeto para Documentos\Xiaomi-TV-Manager
  3) instala ADB, scrcpy e Python (winget, fontes oficiais)  4) cria atalho na Area de Trabalho  5) abre o painel.
  Cada passo e independente: se um falhar, os outros continuam e o resumo final mostra o que aconteceu.
  Reexecutar atualiza o programa sem apagar config.json, historico.json, reports\ e logs\.
#>
$ErrorActionPreference = 'Stop'
$origem  = Split-Path -Parent $PSScriptRoot
$docs    = [Environment]::GetFolderPath('MyDocuments')
$destino = Join-Path $docs 'Xiaomi-TV-Manager'
$resumo  = New-Object System.Collections.Generic.List[string]
$falhas  = 0

New-Item -ItemType Directory -Path (Join-Path $destino 'logs') -Force | Out-Null
$logFile = Join-Path $destino ('logs\instalacao-{0}.log' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
try { Start-Transcript -Path $logFile -Force | Out-Null } catch { }

function Passo([int]$n, [string]$titulo, [scriptblock]$acao) {
    Write-Host ''
    Write-Host ("[{0}/5] {1}" -f $n, $titulo) -ForegroundColor Cyan
    try {
        & $acao
        $script:resumo.Add(("  [OK]    {0}" -f $titulo))
    } catch {
        $script:falhas++
        $script:resumo.Add(("  [FALHA] {0}: {1}" -f $titulo, $_.Exception.Message))
        Write-Host ("ERRO: {0}" -f $_.Exception.Message) -ForegroundColor Red
    }
}

Passo 1 'Desbloquear arquivos baixados' {
    Get-ChildItem -Path $origem -Recurse -File | Unblock-File
}

Passo 2 "Copiar o programa para $destino" {
    if ($origem.TrimEnd('\') -ieq $destino.TrimEnd('\')) { Write-Host 'Ja esta na pasta definitiva.'; return }
    foreach ($item in 'app','scripts','docs','README.md','CHANGELOG.md','INSTALAR.bat','Iniciar-XiaomiTVManager.bat','Preparar-Windows.bat') {
        $src = Join-Path $origem $item
        if (Test-Path $src) { Copy-Item -Path $src -Destination $destino -Recurse -Force }
    }
    foreach ($d in 'data','reports','logs') { New-Item -ItemType Directory -Path (Join-Path $destino $d) -Force | Out-Null }
    Copy-Item (Join-Path $origem 'data\pacotes-conhecidos.json') (Join-Path $destino 'data') -Force
    # Configuracao, historico e relatorios existentes sao preservados
    if (-not (Test-Path (Join-Path $destino 'config.json'))) { Copy-Item (Join-Path $origem 'config.json') $destino }
    $rel = Join-Path $origem 'reports\RELATORIO-DIAGNOSTICO.md'
    if ((Test-Path $rel) -and -not (Test-Path (Join-Path $destino 'reports\RELATORIO-DIAGNOSTICO.md'))) { Copy-Item $rel (Join-Path $destino 'reports') }
    Get-ChildItem -Path $destino -Recurse -File | Unblock-File
    if (-not (Test-Path (Join-Path $destino 'app\xiaomi_tv_manager.py'))) { throw 'arquivos nao foram copiados' }
}

Passo 3 'Instalar ADB, scrcpy e Python (pode levar alguns minutos)' {
    & (Join-Path $destino 'scripts\00-Preparar-Windows.ps1') -SemCopiarProjeto
}

$atalhos = @()
Passo 4 'Criar atalho "Xiaomi TV Manager" na Area de Trabalho e no Menu Iniciar' {
    $script:atalhos = @(& (Join-Path $destino 'scripts\Criar-Atalho.ps1') | Where-Object { $_ -like '*.lnk' })
    if (-not $script:atalhos.Count) { throw 'nenhum atalho foi criado' }
}

Passo 5 'Abrir o painel' {
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
    $app = Join-Path $destino 'app\xiaomi_tv_manager.py'
    . (Join-Path $destino 'scripts\Comum.ps1')
    $ErrorActionPreference = 'Stop'
    $pyw = Find-XtmPython
    if (-not $pyw) { throw 'Python nao encontrado nesta janela (reinicie o PC e use o atalho ou Iniciar-XiaomiTVManager.bat)' }
    Start-Process -FilePath $pyw -ArgumentList "`"$app`"" -WorkingDirectory $destino
}

Write-Host ''
Write-Host '==================== RESUMO ====================' -ForegroundColor Cyan
$resumo | ForEach-Object { if ($_ -like '*FALHA*') { Write-Host $_ -ForegroundColor Red } else { Write-Host $_ -ForegroundColor Green } }
Write-Host ''
Write-Host "Programa instalado em: $destino" -ForegroundColor Yellow
foreach ($a in $atalhos) { Write-Host "Atalho: $a" -ForegroundColor Yellow }
Write-Host "Para abrir manualmente: $destino\Iniciar-XiaomiTVManager.bat"
Write-Host "Log desta instalacao:  $logFile"
if ($falhas) { Write-Host "`nHouve $falhas falha(s). Envie um print desta janela ou o arquivo de log para analise." -ForegroundColor Red }
try { Stop-Transcript | Out-Null } catch { }
# Mostra a pasta do programa no Explorer, para nunca ficar "perdido"
try { Start-Process explorer.exe -ArgumentList "`"$destino`"" } catch { }
