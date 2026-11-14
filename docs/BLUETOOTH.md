# Diagnóstico do Bluetooth e do controle remoto

Ferramentas: aba **Bluetooth** do app ou `scripts\08-Bluetooth.ps1`. **As duas apenas leem dados.** Nenhuma desfaz pareamento, re-pareia ou reinicia o Bluetooth.

## O que o software consegue diagnosticar
| Verificação | Fonte | Como interpretar |
|---|---|---|
| Bluetooth ligado e no estado ON | `dumpsys bluetooth_manager` | Se estiver OFF ou alternando, é problema de sistema |
| Controle pareado (*bonded*) | idem | Se ele não aparecer, o pareamento se perdeu |
| Controle conectado agora | `dumpsys input` (dispositivo com `bus=0x0005` = Bluetooth) | Pareado mas ausente aqui significa desconectado ou dormindo |
| Desconexões e *supervision timeout* | `logcat` (só o período recente, poucas horas) | Muitos timeouts indicam enlace de rádio fraco (sinal ou interferência) |
| Travamentos de apps / ANR | `logcat -b crash`, `*:E` | Se o controle "não responde" só quando o sistema trava, o problema é desempenho, não o Bluetooth |

**Como coletar:** quando o controle falhar, use o painel do PC (que funciona por Wi-Fi) e rode a análise **na hora**. O log é curto.

## O que depende de teste físico
1. **Posição atrás da TV:** metal e eletrônica da TV bloqueiam 2,4 GHz. Teste com o **extensor HDMI**, afastando o Stick do painel.
2. **Pilhas:** troque por pilhas novas antes de qualquer outra conclusão.
3. **Interferência 2,4 GHz:** roteador próximo, HD/pendrive USB 3.0 na TV, micro-ondas. Se puder, use o Wi-Fi de **5 GHz** no Stick (libera a faixa de 2,4 GHz para o Bluetooth).
4. **Distância:** funciona a 1 m e falha a 4 m? É sinal.
5. **Alimentação:** fonte original na tomada, não a USB da TV.
6. **Teste cruzado:** o app Google TV no celular, ou este painel, funciona quando o controle falha? Se sim, o sistema está bem e o problema é o controle/enlace.

## Re-parear (somente com a sua autorização)
**Configurações → Controles e acessórios → [controle] → Esquecer/Desparear**, e depois **Adicionar acessório** e coloque o controle em modo de pareamento conforme o manual (a combinação de botões varia por modelo de controle Xiaomi; confirme no manual ou na tela da TV). O painel do PC continua funcionando durante o processo, então você não fica sem controle.
