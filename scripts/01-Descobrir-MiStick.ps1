<#
.SYNOPSIS
  Procura o Xiaomi Mi TV Stick na rede local de forma nao invasiva.
.DESCRIPTION
  Etapas (do menos para o mais ativo):
    1. Anuncios mDNS de depuracao sem fio (adb mdns services).
    2. Tabela ARP/vizinhos do Windows (dispositivos ja vistos pelo PC) + teste TCP na porta 5555.
    3. (Opcional, -Varredura) ping em cada endereco da sub-rede /24 seguido do teste TCP 5555.
       Envia apenas 1 ping ICMP e 1 tentativa de conexao TCP por endereco.
  Nao faz varredura de portas alem da 5555 e nao tenta autenticacao em nada.
.EXAMPLE
  .\01-Descobrir-MiStick.ps1
  .\01-Descobrir-MiStick.ps1 -Varredura
#>
param([switch]$Varredura, [int]$Porta = 5555)
. "$PSScriptRoot\Comum.ps1"

$achados = New-Object System.Collections.Generic.List[object]

# 1) mDNS (depuracao sem fio - Android 11+)
$adb = Find-XtmTool -Name adb
if ($adb) {
    Write-XtmLog 'Consultando anuncios mDNS de ADB (adb mdns services)...'
    $m = Invoke-XtmAdb mdns services
    Write-Host $m
    foreach ($line in ($m -split "`n")) {
        if ($line -match '_adb(-tls-(connect|pairing))?\._tcp\.?\s+(\d+\.\d+\.\d+\.\d+):(\d+)') {
            $achados.Add([pscustomobject]@{ IP = $Matches[3]; Porta = [int]$Matches[4]; Origem = "mDNS $($Matches[1])"; Nome = '' })
        }
    }
}

# 2) Vizinhos ARP conhecidos
Write-XtmLog 'Lendo a tabela de vizinhos (ARP) do Windows...'
$cfgNet = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1
if (-not $cfgNet) { throw 'Nenhuma interface de rede ativa com gateway foi encontrada.' }
$meuIp = $cfgNet.IPv4Address.IPAddress
$prefixo = ($meuIp -split '\.')[0..2] -join '.'
Write-XtmLog "IP deste PC: $meuIp  | sub-rede considerada: $prefixo.0/24"

$vizinhos = Get-NetNeighbor -AddressFamily IPv4 -InterfaceIndex $cfgNet.InterfaceIndex -ErrorAction SilentlyContinue |
    Where-Object { $_.State -in 'Reachable','Stale','Delay','Probe','Permanent' -and $_.IPAddress -like "$prefixo.*" -and $_.IPAddress -notmatch '\.(0|255)$' -and $_.LinkLayerAddress -ne 'ff-ff-ff-ff-ff-ff' }

$alvos = @($vizinhos | ForEach-Object IPAddress)

# 3) Varredura opcional
if ($Varredura) {
    Write-XtmLog "Varredura leve: 1 ping por endereco em $prefixo.1-254 ..."
    $pings = @{}
    foreach ($i in 1..254) { $ip = "$prefixo.$i"; if ($ip -ne $meuIp) { $pings[$ip] = (New-Object System.Net.NetworkInformation.Ping).SendPingAsync($ip, 600) } }
    try { [System.Threading.Tasks.Task]::WaitAll([System.Threading.Tasks.Task[]]@($pings.Values)) } catch { }
    $alvos += $pings.Keys | Where-Object { $pings[$_].Status -eq 'RanToCompletion' -and $pings[$_].Result.Status -eq 'Success' }
    # Alguns aparelhos nao respondem a ping mas aparecem no ARP depois da tentativa:
    $alvos += Get-NetNeighbor -AddressFamily IPv4 -InterfaceIndex $cfgNet.InterfaceIndex -ErrorAction SilentlyContinue |
        Where-Object { $_.State -in 'Reachable','Stale' -and $_.IPAddress -like "$prefixo.*" } | ForEach-Object IPAddress
}
$alvos = $alvos | Where-Object { $_ -and $_ -ne $meuIp } | Sort-Object { [version]$_ } -Unique

Write-XtmLog ("Testando porta TCP {0} em {1} endereco(s)..." -f $Porta, @($alvos).Count)
foreach ($ip in $alvos) {
    if (Test-XtmTcpPort -Ip $ip -Port $Porta -TimeoutMs 400) {
        $nome = ''
        try { $nome = [System.Net.Dns]::GetHostEntry($ip).HostName } catch { }
        $achados.Add([pscustomobject]@{ IP = $ip; Porta = $Porta; Origem = 'TCP 5555 aberta'; Nome = $nome })
    }
}

if ($achados.Count -eq 0) {
    Write-XtmLog 'Nenhum dispositivo com ADB acessivel foi encontrado.' WARN
    Write-Host ''
    Write-Host 'Proximos passos:' -ForegroundColor Yellow
    Write-Host '  1. Na TV: Configuracoes > Preferencias do dispositivo > Sobre > Status > Endereco IP. Anote o IP.'
    Write-Host '  2. Confirme que a Depuracao USB / ADB esta ativada (docs\MODO-DESENVOLVEDOR.md).'
    Write-Host '  3. Rode:  .\02-Conectar.ps1 -Ip <IP_DA_TV>'
    Write-Host '  4. Ou tente a varredura leve:  .\01-Descobrir-MiStick.ps1 -Varredura'
    exit 1
}

Write-XtmLog 'Possiveis dispositivos encontrados:' OK
$achados | Sort-Object IP -Unique | Format-Table -AutoSize | Out-String -Width 200 | Write-Host
if (@($achados | Sort-Object IP -Unique).Count -eq 1) {
    $cfg = Get-XtmConfig; $cfg.ip = $achados[0].IP
    if ($achados[0].Origem -like 'TCP*') { $cfg.port = $achados[0].Porta }
    Save-XtmConfig $cfg
    Write-XtmLog "IP $($cfg.ip) salvo em config.json. Agora rode .\02-Conectar.ps1" OK
} else {
    Write-Host 'Mais de um candidato. Rode .\02-Conectar.ps1 -Ip <IP> com o IP mostrado na TV.'
}
