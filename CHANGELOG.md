# Histórico de alterações do projeto

## 0.3.0 — 2026-11-14
### Explicações compreensíveis
- Cada app agora aparece com **nome compreensível** (ex.: "Assistente de voz do Google" em vez de `com.google.android.katniss`), **para que serve**, **o que acontece se desativar** e uma **recomendação**: Manter / Pode desativar se não usa / Depende do seu uso / Decisão sua / Não mexer.
- Base ampliada para 89 apps (sistema Android, Google, Xiaomi, Amlogic, streaming), mais 16 regras por família de nome. Assim, quase nenhum item fica sem explicação.
- Apps instalados por você aparecem como "Instalado por você". Streaming continua protegido.
- Aba Otimização: cores por recomendação, filtros em linguagem simples e painel de explicação. A lista de apps do Controle remoto, o Diagnóstico, a tabela exportada e o `09-Otimizar.ps1 -Classificar` também usam os nomes.

## 0.2.5 — 2026-11-14
### Novo
- **Trava da tela inicial:** o app e o `09-Otimizar.ps1` recusam desativar o app que é a tela inicial padrão da TV, ou a única tela inicial instalada. Na dúvida, também recusam.
- **PatchWall** (`com.mitv.tvhome.atv`) deixa de ser protegido e vira "Opcional", podendo ser desativado com a trava acima. Isso é desativar, não desinstalar, e é reversível.
### Corrigido
- O histórico podia **perder uma entrada** quando duas alterações terminavam ao mesmo tempo, e essa alteração ficava sem registro de reversão. As gravações agora são serializadas. Teste com 40 gravações simultâneas incluído: ele falha sem a correção e passa com ela.

## 0.2.4 — 2026-11-14
### Primeira análise com dados reais do aparelho
- Relatório da linha de base: `docs/RELATORIO-DIAGNOSTICO-2026-11-13.md` (MiTV-AYFR0, Android 11, firmware 25.9.9.1546).
### Corrigido
- O uso de RAM por app aparecia exagerado: o programa lia a tabela RSS, que conta em dobro a memória compartilhada (tela inicial: 331 MB em vez de 248 MB). Agora usa a tabela PSS quando o firmware traz as duas.
### Novo
- A coleta completa passa a incluir `dumpsys diskstats` (espaço ocupado por cada app; somente leitura).
- Base de pacotes com os pacotes Xiaomi encontrados no aparelho. `com.mi.bluetooth`, `xiaomi.tvservice`, o serviço de atualização e os componentes da tela inicial ficam protegidos. A telemetria (`com.miui.tv.analytics`) é marcada como candidata.
- Testes com trechos reais das saídas do aparelho (`app/tests/dados_reais`).

## 0.2.3 — 2026-11-14
### Corrigido
- O app mostrava "Conexão perdida" e tentava reconectar sem parar mesmo sem nunca ter conectado. Agora a reconexão automática só age depois de uma conexão bem-sucedida.
- Cada tentativa travava 15 s quando a TV não respondia. Agora a porta é testada antes, em 2,5 s.
### Novo
- Botão **Testar conexão** e diagnóstico automático quando a conexão falha. Ele testa ping, porta e anúncio de "Depuração sem fio", verifica se PC e TV estão na mesma rede e explica em português o que fazer. Se a TV anunciar a porta da depuração sem fio, ela é preenchida automaticamente.

## 0.2.2 — 2026-11-14
### Corrigido
- O painel não abria quando o PC tinha um Python registrado num caminho que não existe mais (ex.: `E:\python311`). Aparecia o erro "Python Launcher is sorry to say... Unable to create process".
  - O instalador agora **testa** cada Python (se executa e se tem Tkinter) em vez de só verificar se o `py.exe` existe. Se nenhum funcionar, instala o Python 3.12.
  - O Python escolhido fica gravado em `data\python.txt` e `config.json`.
  - O `Iniciar-XiaomiTVManager.bat` não usa mais o `pyw` padrão: lê `data\python.txt` e, se precisar, procura o Python nas pastas de instalação.

## 0.2.1 — 2026-11-14
### Corrigido
- O instalador podia parar no passo 4 (atalho) no Windows PowerShell 5.1 por causa de `Join-Path` com caminho vazio. Assim o atalho não era criado e o painel não abria.
- Comandos externos com saída em stderr (scrcpy, py, winget) podiam abortar o `00-Preparar-Windows.ps1` no PowerShell 5.1.
### Melhorado
- O instalador continua mesmo se um passo falhar, mostra um resumo (OK/FALHA), grava o log em `logs\instalacao-*.log`, informa onde o programa e os atalhos ficaram e abre a pasta do programa no Explorer.

## 0.2.0 — 2026-11-13
### Simplificado
- `INSTALAR.bat` + `scripts/Instalar.ps1`: instalação, cópia para Documentos, atalho e abertura do painel em um clique. Avisa quando o arquivo é aberto de dentro do ZIP.
- Assistente de conexão no painel: abre na primeira execução, mostra o que fazer na TV, procura a TV na rede, conecta e espera a autorização.
- O ADB passa a ser encontrado também em `WinGet\Links`.
- Corrigido: o `00-Preparar-Windows.ps1` sobrescrevia a variável automática `$profile`.

> Alterações feitas **no Mi Stick** (pacotes, configurações) não ficam aqui. Elas ficam em `data\historico.json` e aparecem na aba **Histórico e reversão**.

## 0.1.0 — 2026-11-13
### Criado
- Scripts PowerShell `00`–`09` + `Comum.ps1` + `Criar-Atalho.ps1`: preparação do Windows (winget), descoberta não invasiva, conexão (TCP 5555 e pareamento sem fio), espelhamento scrcpy, controle por teclado, diagnóstico somente leitura, reconexão automática, abertura de apps, Bluetooth e otimização com histórico e reversão.
- App **Xiaomi TV Manager** (Python/Tkinter, só biblioteca padrão): abas Conexão, Controle remoto, Diagnóstico, Otimização, Histórico e reversão, Bluetooth.
- Base `data/pacotes-conhecidos.json` com proteção por prefixo (sistema, Google, Cast, Bluetooth, Wi-Fi, DRM/Amlogic, streaming).
- Testes: 15 unitários + simulação de ponta a ponta do app (19 verificações) contra um ADB **simulado**.

### Validado (sem o aparelho)
- Sintaxe de todos os `.ps1` no parser do PowerShell 7.4. Lógica de `04`, `05`, `06`, `07`, `08` e `09` executada contra o ADB simulado.
- App gráfico executado em tela virtual (Linux/Xvfb, Python 3.12) contra o ADB simulado.

### Ainda NÃO validado
- Qualquer interação com o Mi TV Stick real, Windows real, winget, scrcpy real e descoberta na rede (`00`, `01`, `03`).
