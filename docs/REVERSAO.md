# Procedimentos de reversão

Todas as alterações feitas pelo app ou por `09-Otimizar.ps1` ficam em `data\historico.json`, com o **estado anterior** e o **comando exato de reversão**.

## Pelo app
Aba **Histórico e reversão** → selecione → **Reverter selecionado**, ou **Reverter tudo** (da mais recente para a mais antiga).
**Exportar procedimento de reversão** gera um `.txt` em `reports\` com os comandos prontos.

## Pelo PowerShell
```powershell
.\scripts\09-Otimizar.ps1 -Historico
.\scripts\09-Otimizar.ps1 -Reverter 3
.\scripts\09-Otimizar.ps1 -ReverterTudo
```

## Manualmente (sem o projeto)
| Alteração | Reverter |
|---|---|
| Pacote desativado | `adb shell pm enable --user 0 <pacote>` |
| Ver os desativados | `adb shell pm list packages -d` |
| Animação alterada | `adb shell settings put global window_animation_scale 1.0` (o mesmo para `transition_animation_scale` e `animator_duration_scale`) ou `settings delete global <chave>` se antes era `null` |

Pela própria TV: **Configurações → Apps → Ver todos → Apps do sistema / desativados → [app] → Ativar**. Animações: **Opções do desenvolvedor → Escala de animação → 1x**.

## O que este projeto nunca faz
Root, desbloqueio de bootloader, restauração de fábrica, `pm clear` (apagar dados), `pm uninstall` (remoção) e alteração de pareamento Bluetooth. Por isso, toda alteração possível é reversível com os comandos acima.
