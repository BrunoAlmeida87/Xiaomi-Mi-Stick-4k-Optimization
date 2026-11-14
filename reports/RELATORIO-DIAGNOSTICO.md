# Relatório de diagnóstico — Xiaomi Mi TV Stick 4K

**Status: PENDENTE — nenhuma coleta real foi feita ainda.**

O projeto foi criado num ambiente na nuvem, sem acesso à sua rede local, então não há dados reais do aparelho. Os valores abaixo serão preenchidos pelas coletas.

## Como gerar
1. Conecte (`02-Conectar.ps1` ou o app).
2. **Linha de base, antes de qualquer alteração:** `.\scripts\05-Diagnostico.ps1` ou **Diagnóstico → Coleta completa**. Faça a coleta cerca de 10 minutos depois de ligar, sem app aberto.
3. Gere a classificação real: `.\scripts\09-Otimizar.ps1 -Classificar`.
4. Bluetooth: `.\scripts\08-Bluetooth.ps1`, logo após uma falha do controle, se houver.
5. Depois das otimizações aprovadas, faça outra coleta nas mesmas condições e use **Comparar 2 últimas coletas**.

## Linha de base (preencher)
| Item | Valor |
|---|---|
| Modelo / Android / Firmware | |
| RAM total / disponível | |
| Swap/ZRAM em uso | |
| /data usado / livre | |
| Load average | |
| Maiores consumidores de RAM | |
| Animações | |
| Bluetooth / controle | |

## Referência (especificação pública, não medida)
O Mi TV Stick 4K é vendido com Android TV 11, 2 GB de RAM e 8 GB de armazenamento. Por isso, RAM disponível na faixa de algumas centenas de MB é normal para esse hardware.
