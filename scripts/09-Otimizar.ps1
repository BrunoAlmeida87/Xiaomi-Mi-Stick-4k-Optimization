<#
.SYNOPSIS
  Classifica pacotes e aplica/reverte otimizacoes com confirmacao, registro do estado anterior e reversao.
.DESCRIPTION
  Toda alteracao e gravada em data\historico.json (mesmo arquivo usado pelo app grafico).
  Usa apenas "pm disable-user --user 0" (reversivel com "pm enable"). Nunca desinstala, nunca limpa dados.
  Pacotes Essenciais/protegidos (launcher, Play, GMS, Cast, Bluetooth, Wi-Fi, DRM, streaming) sao recusados.
.EXAMPLE
  .\09-Otimizar.ps1 -Classificar                       # tabela de classificacao (somente leitura)
  .\09-Otimizar.ps1 -Desativar com.google.android.backdrop
  .\09-Otimizar.ps1 -Animacoes 0.5                     # 1 = padrao; 0.5 = metade; 0 = desligadas
  .\09-Otimizar.ps1 -Historico
  .\09-Otimizar.ps1 -Reverter 3                        # reverte a entrada de id 3
  .\09-Otimizar.ps1 -ReverterTudo
#>
param([switch]$Classificar, [string[]]$Desativar, [string]$Animacoes, [switch]$Historico, [int]$Reverter = 0, [switch]$ReverterTudo, [switch]$Sim)
. "$PSScriptRoot\Comum.ps1"
$serial = Get-XtmSerial
$histFile = Join-Path $XtmRoot 'data\historico.json'
$db = Get-Content (Join-Path $XtmRoot 'data\pacotes-conhecidos.json') -Raw -Encoding UTF8 | ConvertFrom-Json

function Get-Hist { if (Test-Path $histFile) { $h = Get-Content $histFile -Raw -Encoding UTF8 | ConvertFrom-Json; return @($h) } return @() }
function Save-Hist($h) { ConvertTo-Json -InputObject @($h) -Depth 6 | Set-Content $histFile -Encoding UTF8 }
function Add-Hist($tipo, $alvo, $antes, $depois, [string[]]$reverter, $resultado) {
    $h = @(Get-Hist); $id = 1; if ($h.Count) { $id = ([int]($h | Measure-Object -Property id -Maximum).Maximum) + 1 }
    $e = [pscustomobject]@{ id = $id; timestamp = (Get-Date -Format 's'); origem = 'powershell'; tipo = $tipo; alvo = $alvo; antes = $antes; depois = $depois; reverter = $reverter; resultado = $resultado; revertido = $false }
    Save-Hist (@($h) + $e); return $e
}

function Test-Protegido([string]$p) {
    foreach ($pre in $db.protegidos_prefixo) {
        if ($pre.EndsWith('.')) { if ($p.StartsWith($pre)) { return $true } }
        elseif ($p -eq $pre -or $p.StartsWith("$pre.")) { return $true }
    }
    $info = $db.pacotes.PSObject.Properties[$p]
    return ($info -and $info.Value.cat -eq 'Essencial')
}
$Recom = @{ 'Essencial' = 'Manter (necessario)'; 'Opcional' = 'Depende do seu uso'; 'Candidato' = 'Pode desativar se nao usa'; 'Instalado por voce' = 'Decisao sua'; 'Desconhecido' = 'Nao mexer (sem informacao)' }
function Get-Info([string]$p, [switch]$Terceiro) {
    $prot = Test-Protegido $p
    $info = $db.pacotes.PSObject.Properties[$p]
    if ($info) { $v = $info.Value; $cat = $(if ($prot) { 'Essencial' } else { $v.cat })
        return [pscustomobject]@{ cat = $cat; nome = $v.nome; funcao = $v.funcao; efeito = $v.efeito; impacto = $v.impacto } }
    if ($Terceiro -and -not $prot) {
        return [pscustomobject]@{ cat = 'Instalado por voce'; nome = $p; funcao = 'App instalado pela Play Store.'; efeito = 'O app some ate ser reativado.'; impacto = '?' } }
    foreach ($r in @($db.regras)) {
        $ok = $false
        if ($r.PSObject.Properties['prefixo'] -and $p.StartsWith($r.prefixo)) { $ok = $true }
        if ($r.PSObject.Properties['contem'] -and $p.Contains($r.contem)) { $ok = $true }
        if ($ok) { return [pscustomobject]@{ cat = $(if ($prot) { 'Essencial' } else { $r.cat }); nome = $r.nome; funcao = $r.funcao; efeito = $r.efeito; impacto = '-' } }
    }
    if ($prot) { return [pscustomobject]@{ cat = 'Essencial'; nome = 'Componente protegido do sistema'; funcao = 'Parte do sistema, do Google ou de streaming.'; efeito = 'Protegido.'; impacto = '-' } }
    return [pscustomobject]@{ cat = 'Desconhecido'; nome = $p; funcao = 'Funcao nao identificada.'; efeito = 'Desconhecido - nao mexa sem pesquisar.'; impacto = '?' }
}
function Get-PkgSet([string]$flag) { (Invoke-XtmShell -Serial $serial -Command "pm list packages $flag") -split "`n" | Where-Object { $_ -match '^package:' } | ForEach-Object { $_.Substring(8).Trim() } }

if ($Classificar) {
    $sist = @(Get-PkgSet '-s'); $terc = @(Get-PkgSet '-3'); $des = @(Get-PkgSet '-d')
    $linhas = foreach ($p in ($sist + $terc | Sort-Object -Unique)) {
        $i = Get-Info $p -Terceiro:($terc -contains $p)
        [pscustomobject]@{ Nome = $i.nome; Recomendacao = $Recom[$i.cat]; Estado = $(if ($des -contains $p) { 'desativado' } else { 'ativo' }); ParaQueServe = $i.funcao; SeDesativar = $i.efeito; Pacote = $p; Categoria = $i.cat }
    }
    $ordem = @{ 'Candidato' = 0; 'Opcional' = 1; 'Instalado por voce' = 2; 'Desconhecido' = 3; 'Essencial' = 4 }
    $linhas = $linhas | Sort-Object @{ e = { $ordem[$_.Categoria] } }, Nome
    $linhas | Format-Table Nome, Recomendacao, Estado, Pacote -AutoSize | Out-String -Width 250 | Write-Host
    $csv = Join-Path $XtmReports ('classificacao-{0}.csv' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
    $linhas | Export-Csv -Path $csv -NoTypeInformation -Encoding UTF8 -Delimiter ';'
    Write-XtmLog "Tabela salva em $csv (abre no Excel)." OK
    exit 0
}

if ($Desativar) {
    $Desativar = @($Desativar | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $des = @(Get-PkgSet '-d'); $todos = @(Get-PkgSet '')
    foreach ($p in $Desativar) {
        if ($todos -notcontains $p) { Write-XtmLog "$p nao esta instalado." WARN; continue }
        if (Test-Protegido $p) { Write-XtmLog "$p e protegido/essencial. Recusado." ERRO; continue }
        # Nunca desativar a tela inicial padrao nem a unica tela inicial instalada
        $hd = (Invoke-XtmShell -Serial $serial -Command 'cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME') -split "`n" | Where-Object { $_ -match '^\s*([A-Za-z][\w.]*)/' } | ForEach-Object { ($_.Trim() -split '/')[0] }
        $ha = @((Invoke-XtmShell -Serial $serial -Command 'cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.HOME') -split "`n" | Where-Object { $_ -match '^\s*([A-Za-z][\w.]*)/' } | ForEach-Object { ($_.Trim() -split '/')[0] } | Where-Object { $_ -notin 'com.android.tv.settings','com.android.settings' } | Sort-Object -Unique)
        if (@($hd) -contains $p) { Write-XtmLog "$p e a tela inicial PADRAO da TV. Recusado." ERRO; continue }
        if (($ha -contains $p) -and $ha.Count -le 1) { Write-XtmLog "$p e a UNICA tela inicial instalada. Recusado." ERRO; continue }
        if (-not @($hd).Count -and -not $ha.Count) { Write-XtmLog 'Nao foi possivel confirmar a tela inicial; nada foi alterado.' ERRO; continue }
        if ($des -contains $p) { Write-XtmLog "$p ja esta desativado." INFO; continue }
        $i = Get-Info $p
        Write-Host ("`n{0}`nPara que serve: {1}`nSe desativar: {2}`nNome tecnico: {3}`nReversao: pm enable --user 0 {3}" -f $i.nome, $i.funcao, $i.efeito, $p) -ForegroundColor Yellow
        if ($i.cat -eq 'Desconhecido') {
            if ((Read-Host "Pacote NAO classificado. Digite o nome completo do pacote para confirmar") -ne $p) { Write-XtmLog 'Cancelado.'; continue }
        } elseif (-not $Sim) {
            if ((Read-Host 'Confirmar desativacao? (s/N)') -notmatch '^[sS]') { Write-XtmLog 'Cancelado.'; continue }
        }
        $r = (Invoke-XtmShell -Serial $serial -Command "pm disable-user --user 0 $p").Trim()
        $ok = $r -match 'disabled-user'
        $e = Add-Hist 'pacote' $p 'enabled' $(if ($ok) { 'disabled-user' } else { 'falhou' }) @('pm','enable','--user','0',$p) $r
        if ($ok) { Write-XtmLog "Desativado: $p (historico id $($e.id))" OK } else { Write-XtmLog "Falhou: $r" ERRO }
    }
    exit 0
}

if ($Animacoes) {
    $v = [double]::Parse($Animacoes, [Globalization.CultureInfo]::InvariantCulture)
    if ($v -lt 0 -or $v -gt 10) { throw 'Valor deve estar entre 0 e 10.' }
    foreach ($k in 'window_animation_scale','transition_animation_scale','animator_duration_scale') {
        $antes = (Invoke-XtmShell -Serial $serial -Command "settings get global $k").Trim()
        Write-Host "$k : $antes -> $Animacoes"
    }
    if (-not $Sim -and (Read-Host 'Aplicar? (s/N)') -notmatch '^[sS]') { Write-XtmLog 'Cancelado.'; exit 0 }
    foreach ($k in 'window_animation_scale','transition_animation_scale','animator_duration_scale') {
        $antes = (Invoke-XtmShell -Serial $serial -Command "settings get global $k").Trim()
        Invoke-XtmShell -Serial $serial -Command ("settings put global $k {0}" -f $v.ToString([Globalization.CultureInfo]::InvariantCulture)) | Out-Null
        $depois = (Invoke-XtmShell -Serial $serial -Command "settings get global $k").Trim()
        if ($antes -eq 'null') { $rev = @('settings','delete','global',$k) } else { $rev = @('settings','put','global',$k,$antes) }
        $e = Add-Hist 'configuracao' $k $antes $depois $rev 'ok'
        Write-XtmLog "$k : $antes -> $depois (id $($e.id))" OK
    }
    exit 0
}

function Invoke-Reverter($e) {
    if ($e.revertido) { Write-XtmLog "Entrada $($e.id) ja revertida."; return $e }
    $cmd = ($e.reverter -join ' ')
    $r = (Invoke-XtmShell -Serial $serial -Command $cmd).Trim()
    Write-XtmLog "Revertendo $($e.id) [$($e.alvo)]: $cmd -> $r" OK
    $e.revertido = $true
    return $e
}

if ($Reverter -gt 0 -or $ReverterTudo) {
    $h = @(Get-Hist)
    $alvos = if ($ReverterTudo) { $h | Where-Object { -not $_.revertido -and $_.depois -ne 'falhou' } | Sort-Object id -Descending } else { $h | Where-Object id -eq $Reverter }
    if (-not $alvos) { Write-XtmLog 'Nada a reverter.' WARN; exit 0 }
    foreach ($e in $alvos) { Invoke-Reverter $e | Out-Null }
    Save-Hist $h
    exit 0
}

# Padrao (ou -Historico): mostra o historico
if ($true) {
    $h = @(Get-Hist)
    if (-not $h.Count) { Write-Host 'Historico vazio (nenhuma alteracao feita).'; exit 0 }
    $h | Format-Table id, timestamp, origem, tipo, alvo, antes, depois, revertido, @{n='reverter';e={$_.reverter -join ' '}} -AutoSize | Out-String -Width 250 | Write-Host
}
