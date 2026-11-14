# Ativar a depuração ADB no Xiaomi Mi TV Stick 4K

Use o controle original uma última vez. Depois disso, o PC passa a controlar o Stick.

## 1. Ativar as Opções do desenvolvedor
1. **Configurações** (engrenagem) → **Preferências do dispositivo** → **Sobre**.
2. Desça até **Build** (ou "Versão do Android TV OS") e pressione **OK 7 vezes** até aparecer *"Agora você é um desenvolvedor"*.
3. Volte para **Preferências do dispositivo**. Agora existe **Opções do desenvolvedor**.

## 2. Ligar a depuração
Em **Opções do desenvolvedor**:
- Ative **Depuração USB**. Em muitos firmwares de Android TV, isso também libera o ADB pela rede na porta **5555**.
- Se existir **Depuração sem fio** (*Wireless debugging*, comum no Android 11+), ative também. Ela usa **outra porta** e exige pareamento com código.
- (Opcional) Se houver **Depuração de rede** / *ADB over network*, ative.

> Não presumimos qual método o seu firmware aceita: os scripts testam os dois.

## 3. Descobrir o IP
**Configurações → Preferências do dispositivo → Sobre → Status → Endereço IP** (ou **Configurações → Rede e Internet → [sua rede]**).
Dica: reserve esse IP no roteador (DHCP estático) para a reconexão automática não se perder.

## 4. Conectar pelo PC
```powershell
.\scripts\02-Conectar.ps1 -Ip 192.168.X.Y
```
Na TV, aparece **"Permitir depuração USB?"**. Marque **"Sempre permitir deste computador"** e escolha **OK**.

### Se a porta 5555 não responder (depuração sem fio)
1. Em **Opções do desenvolvedor → Depuração sem fio**, anote o **IP:porta** mostrado na tela.
2. Escolha **Parear dispositivo com código de pareamento** e anote o **IP:porta de pareamento** e o **código de 6 dígitos**.
3. No PC:
```powershell
.\scripts\02-Conectar.ps1 -Parear -EnderecoPareamento 192.168.X.Y:PORTA_PAREAMENTO -Codigo 123456 -Ip 192.168.X.Y -Porta PORTA_DEPURACAO
```
A porta da depuração sem fio muda a cada reinício do Stick. A porta 5555, quando disponível, é fixa.

## Problemas comuns
| Sintoma | Causa provável | Solução |
|---|---|---|
| `failed to connect` / `refused` | Depuração desligada ou o firmware não abre a 5555 | Revise o passo 2 e tente a depuração sem fio |
| `unauthorized` | O pedido de autorização na TV não foi aceito | Aceite na TV. Se o pedido sumiu, rode `adb kill-server` e conecte de novo |
| `offline` | A TV entrou em suspensão ou a rede caiu | `06-Reconectar.ps1` ou o botão Conectar |
| Conecta e cai após desligar a TV | O Stick dorme quando a TV desliga | Esperado. A reconexão automática retoma a conexão quando a TV liga |
| PC e TV em redes diferentes (Wi-Fi visitante, *AP isolation*) | O roteador bloqueia o tráfego entre aparelhos | Coloque os dois na mesma rede principal |
| Firewall do Windows pergunta sobre o adb.exe | É o adb abrindo o servidor local | Permita só em **Redes privadas**. Não é preciso desativar o firewall |

## Para desligar tudo depois
**Opções do desenvolvedor → Depuração USB: desativar.** Para revogar computadores autorizados: **Revogar autorizações de depuração USB**.
