# Relatório de diagnóstico: Mi TV Stick 4K (linha de base)

- **Coleta:** `reports\diagnostico-20261113-212300`. A TV estava ligada havia cerca de 37 minutos e o app Configurações estava aberto.
- **Arquivos analisados:** `01-getprop`, `02-meminfo`, `03-dumpsys-meminfo`, `04-armazenamento`, `05-cpuinfo`.
- **Ainda não analisados:** processos (`06-top`), Wi-Fi (`19`), Bluetooth (`20`), lista de apps (`11`/`12`), animações (`14`), uso de apps (`15`) e logs.
- **Nenhuma alteração foi feita no aparelho.**

## Aparelho
| Item | Valor |
|---|---|
| Modelo | Xiaomi **MiTV-AYFR0** (codinome `soul`) |
| Processador | Amlogic S4 (S905Y4), **4 × ARM Cortex-A35**. Sistema 32 bits (`armeabi-v7a`) |
| Android TV | **11** (SDK 30) |
| Firmware | **25.9.9.1546**, de 09/09/2025 |
| Patch de segurança | **2025-08-01** |
| Inicialização verificada | `green`, bootloader travado (sem modificações) |
| Wi-Fi / Bluetooth | Chip combinado **MediaTek MT7663** (o mesmo rádio faz Wi-Fi e Bluetooth) |
| Controles registrados para ligar a TV | **2** endereços Bluetooth |

## Memória RAM
| Medida | Valor | Leitura |
|---|---|---|
| Total visível ao sistema | 1.990 MB | Por volta de 668 MB ficam reservados para o vídeo (CMA) |
| **Disponível (MemAvailable)** | **614 MB (31%)** | Bom para este aparelho |
| Swap (ZRAM, memória comprimida) | 229 MB em uso de 995 MB | Uso moderado e normal |
| Apps em cache (o sistema libera quando precisa) | 377 MB | Não é desperdício |
| Estado informado pelo Android | **normal** | Sem pressão de memória no momento |

**Conclusão:** a RAM **não é o gargalo** agora.

### Maiores consumidores (PSS, memória real)
| App/processo | MB | Situação | Observação |
|---|---|---|---|
| Tela inicial Google (`tvlauncher`) | 248 | visível | Pesada, mas essencial. Menos canais/linhas na tela inicial reduzem esse uso |
| Sistema Android (`system`) | 112 | sistema | Normal |
| Google Play Services (`gms`) | 100 | visível | Essencial (contas, DRM, Cast) |
| `com.mitv.dream` (provável protetor de tela Xiaomi) | 94 | **cache** | O sistema libera quando precisa |
| Assistente/voz (`katniss`, 2 processos) | 88 | visível + cache | Só dispensável se você **nunca** usa voz |
| ProtonVPN (instalado por você) | 58 | cache | Se ficar sempre ligado, todo o tráfego passa pela VPN |
| Play Store (`vending`) | 54 | cache | Essencial |
| Configurações | 50 | em uso | Estava aberto durante a coleta |
| Recomendações (`tvrecommendations`) | 48 | visível | Opcional: alimenta as linhas da tela inicial |
| Netflix | 44 | serviço | Normal e protegido |
| Google TV / Play Filmes (`videos`) | 32 | cache | Candidato se você não compra/aluga filmes no Google |
| Spotify | 30 | perceptível | Serviço Spotify Connect |
| Telemetria Xiaomi (`miui.tv.analytics`) | 15 | **sempre ativo** | Candidato |

## Armazenamento: ponto de atenção
| Partição | Tamanho | Usado | Livre |
|---|---|---|---|
| `/data` (apps e dados) | 4,8 GB | 4,0 GB (**86%**) | **686 MB** |

Com menos de cerca de 1 GB livre, o Android fica mais lento (a manutenção dos apps fica prejudicada) e as atualizações de apps podem falhar. **Este é o problema mais concreto encontrado.** O próximo diagnóstico vai incluir `26-diskstats`, que mostra quanto cada app ocupa.

## Processador
O **Cortex-A35** é o núcleo ARM de menor desempenho da sua geração, e o sistema roda em 32 bits. **Parte da lentidão é do próprio hardware**: nenhuma otimização por software muda isso. O que melhora a sensação de rapidez: menos animação, menos coisa rodando em segundo plano e uma tela inicial mais leve.

## Bluetooth (indícios)
- O Wi-Fi e o Bluetooth usam o **mesmo chip** (MT7663). Se o Stick estiver no Wi-Fi de **2,4 GHz**, ele disputa o rádio com o controle. Usar **5 GHz** costuma melhorar o controle. Para confirmar a banda atual, falta o arquivo `19-wifi.txt`.
- Há **2 controles** registrados para ligar a TV. Se você só usa um, o outro pode ser um controle antigo. Não remova nada sem decidir antes.

## Plano proposto (cada item precisa da sua aprovação)
| # | Ação | Ganho esperado | Risco | Reversão |
|---|---|---|---|---|
| 1 | Liberar armazenamento (identificar com `diskstats`; limpar só o **cache** de apps grandes; desinstalar apps **seus** que não usa) | Alto (fluidez e atualizações) | Baixo | Os apps recriam o cache sozinhos |
| 2 | Animações em 0,5× | Navegação mais rápida (percebido) | Muito baixo | Voltar para 1× |
| 3 | Wi-Fi do Stick em 5 GHz | Controle remoto e streaming mais estáveis | Baixo | Voltar para a rede anterior |
| 4 | Desativar `com.miui.tv.analytics` | ~15 MB sempre livres e menos rede | Baixo | `pm enable --user 0 com.miui.tv.analytics` |
| 5 | Desativar `com.google.android.videos` (se não usa) | ~32 MB e menos sincronização | Baixo | `pm enable --user 0 com.google.android.videos` |
| 6 | Desativar `tvrecommendations` (opcional) | ~48 MB e menos atividade | Médio: linhas da tela inicial podem esvaziar | `pm enable` |
| 7 | Desativar o Assistente/`katniss` (só se nunca usa voz) | ~88 MB | Alto: o botão de voz para de funcionar | `pm enable` |
| 8 | ProtonVPN: só ligar quando precisar | Depende do uso | Decisão sua | — |

**Ganho realista em RAM com os itens 4 a 7: cerca de 50 a 180 MB.** O que você vai sentir mais vem dos itens 1, 2 e 3.

## Decisões do usuário (14/11)
| Item | Decisão |
|---|---|
| Assistente/voz (`com.google.android.katniss`) | **Não usa.** Pode desativar |
| ProtonVPN | **Usa.** Manter |
| Google TV / Play Filmes (`com.google.android.videos`) | **Não usa.** Pode desativar |
| Play Store (`com.android.vending`) | Manter: é ela que atualiza Netflix, YouTube e os outros apps (regra do projeto) |
| PatchWall (`com.mitv.tvhome.atv`) | **Não usa.** Pode desativar, se não for a tela inicial padrão (o app verifica) |
| Telemetria Xiaomi (`com.miui.tv.analytics`) | Aguardando aprovação |
| Animações 0,5× | Aguardando aprovação |

## Próxima coleta
Atualize o programa, volte à **tela inicial** (sem o app Configurações aberto) e rode **Diagnóstico → Coleta completa** de novo. Envie a pasta inteira (ou pelo menos `06`, `12`, `14`, `15`, `19`, `20` e `26-diskstats`).
