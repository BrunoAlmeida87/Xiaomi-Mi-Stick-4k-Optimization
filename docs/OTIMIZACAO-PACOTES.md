# Aplicativos explicados: o que é cada um e se pode desativar

Esta é a base que o programa usa para explicar os apps (`data/pacotes-conhecidos.json`). No aparelho, a tabela real é gerada pela aba **Otimização** e salva em `reports\classificacao-*.md`.

## Recomendações

| Recomendação | Significado | O programa deixa desativar? |
|---|---|---|
| **Manter (necessário)** | Necessário para a TV, o Google Play, o Chromecast, o Bluetooth, o Wi-Fi, a proteção de vídeo (DRM) ou o streaming | **Não** (bloqueado) |
| **Pode desativar se não usa** | Provavelmente dispensável. Confirme que não usa (veja *Último uso* no programa) | Sim, com confirmação |
| **Depende do seu uso** | Tem um efeito visível ao desativar; depende de você usar ou não | Sim, com confirmação |
| **Decisão sua** | App instalado pela Play Store (exceto streaming, que é protegido) | Sim, com confirmação |
| **Não mexer (sem informação)** | Função não identificada | Só digitando o nome técnico completo |

Também há uma **trava de tela inicial**: o programa nunca desativa o app que é a tela inicial padrão, nem a única tela inicial instalada.

## Apps conhecidos

| O que é | Recomendação | Para que serve | Se desativar | Impacto medido | Nome técnico |
|---|---|---|---|---|---|
| **Curiosidade do Android (easter egg)** | Pode desativar se não usa | Brincadeira escondida nas versões do Android. | Nada perceptível. | Nulo | `com.android.egg` |
| **Estatísticas de uso da Xiaomi (telemetria)** | Pode desativar se não usa | Coleta e envia dados de uso para a Xiaomi. | Nenhuma função visível muda. | ~15 MB sempre ativo | `com.miui.tv.analytics` |
| **Google Play Games** | Pode desativar se não usa | Conquistas e jogos do Google. | Só afeta quem joga. | Baixo-médio | `com.google.android.play.games` |
| **Google Play Música (descontinuado)** | Pode desativar se não usa | Serviço de música que o Google encerrou. | Nada perceptível. | Baixo | `com.google.android.music` |
| **Google TV / Play Filmes** | Pode desativar se não usa | Loja de filmes do Google. | Você perde acesso a filmes comprados no Google. | Médio (~32 MB medido) | `com.google.android.videos` |
| **Modo ambiente (fotos no descanso)** | Pode desativar se não usa | Mostra fotos e informações quando a TV fica parada. | O descanso de tela volta ao básico. | Baixo-médio | `com.google.android.backdrop` |
| **Serviço de impressão** | Pode desativar se não usa | Imprimir documentos — algo que não se faz na TV. | Nada perceptível. | Muito baixo | `com.android.printspooler` |
| **YouTube Music** | Pode desativar se não usa | App de música do YouTube. | Só afeta quem usa (o YouTube normal continua). | Baixo | `com.google.android.youtube.tvmusic` |
| **Assistente de voz do Google** | Depende do seu uso | Botão de voz do controle, Google Assistente e busca por voz. | O botão de voz e a busca da tela inicial param; a busca digitada dentro dos apps continua. | Médio (~88 MB medido) | `com.google.android.katniss` |
| **Comandos de voz offline** | Depende do seu uso | Reconhece comandos de voz sem internet. | Pode afetar comandos de voz. | Baixo | `com.google.android.speech.pumpkin` |
| **Envio de feedback** | Depende do seu uso | Envia relatórios de problemas ao Google. | Nada perceptível. | Muito baixo | `com.google.android.feedback` |
| **Equalizador de áudio** | Depende do seu uso | Efeitos de som usados por alguns apps de música. | Alguns apps podem perder o equalizador. | Baixo | `com.android.musicfx` |
| **Gravação de desempenho** | Depende do seu uso | Ferramenta de desenvolvedor para medir desempenho. | Nada perceptível para uso normal. | Nulo quando parado | `com.android.traceur` |
| **PatchWall (Xiaomi)** | Depende do seu uso | Interface de conteúdo da Xiaomi. Você não usa. | Atalhos do PatchWall (e o botão dele no controle, se houver) param. O programa bloqueia se for a tela inicial. | ~30 MB medido | `com.mitv.tvhome.atv` |
| **Protetor de tela da Xiaomi (provável)** | Depende do seu uso | 'Dream' é como o Android chama o protetor de tela. | O protetor de tela pode mudar; prefira trocá-lo nas Configurações. | ~94 MB, mas em cache | `com.mitv.dream` |
| **ProtonVPN** | Depende do seu uso | VPN instalada por você. | A VPN some até ser reativada. Você usa: manter. | ~58 MB medido | `ch.protonvpn.android` |
| **Recomendações da tela inicial** | Depende do seu uso | Preenche as linhas de sugestões na tela inicial. | Algumas linhas da tela inicial podem ficar vazias. | Médio (~48 MB medido) | `com.google.android.tvrecommendations` |
| **TalkBack (leitor de tela)** | Depende do seu uso | Lê a tela em voz alta, para acessibilidade. | Só afeta quem precisa de acessibilidade. | Nulo quando desligado | `com.google.android.marvin.talkback` |
| **YouTube Kids** | Depende do seu uso | YouTube para crianças. | Só afeta quem usa. | Baixo | `com.google.android.youtube.tvkids` |
| **Acesso a pendrive / HD externo** | Manter (necessário) | Permite ler pendrives e HDs ligados na TV. | Pendrives deixariam de funcionar. | - | `com.android.externalstorage` |
| **Armazenamento das configurações** | Manter (necessário) | Guarda todas as configurações do sistema. | O sistema não funcionaria. | - | `com.android.providers.settings` |
| **Assistente de configuração inicial** | Manter (necessário) | Aparece quando a TV é configurada pela primeira vez. | Configurações e atualizações podem falhar; mantenha. | - | `com.google.android.tungsten.setupwraith` |
| **Atualizador de segurança** | Manter (necessário) | Atualiza listas de segurança do sistema. | Sem ganho real; mantenha. | - | `com.google.android.configupdater` |
| **Atualizações do sistema (Xiaomi)** | Manter (necessário) | Baixa atualizações de sistema e de segurança. | Você deixaria de receber atualizações de segurança. | - | `com.xiaomi.mitv.updateservice` |
| **Avisos de VPN** | Manter (necessário) | Necessário para apps de VPN, como o ProtonVPN. | O ProtonVPN deixaria de funcionar. | - | `com.android.vpndialogs` |
| **Backup de armazenamento** | Manter (necessário) | Parte do sistema de backup. | Sem ganho real; mantenha. | - | `com.android.sharedstoragebackup` |
| **Backup do papel de parede** | Manter (necessário) | Guarda o fundo de tela em backups. | Sem ganho real; mantenha. | - | `com.android.wallpaperbackup` |
| **Backup local** | Manter (necessário) | Parte do sistema de backup. | Sem ganho real; mantenha. | - | `com.android.localtransport` |
| **Biblioteca de mídia** | Manter (necessário) | Organiza fotos, vídeos e músicas guardados no aparelho ou pendrive. | Apps não achariam arquivos de mídia. | - | `com.android.providers.media` |
| **Biblioteca de mídia** | Manter (necessário) | Organiza fotos, vídeos e músicas guardados no aparelho ou pendrive. | Apps não achariam arquivos de mídia. | - | `com.android.providers.media.module` |
| **Bibliotecas compartilhadas** | Manter (necessário) | Código usado por vários apps. | Apps poderiam falhar. | - | `com.google.android.ext.shared` |
| **Bluetooth** | Manter (necessário) | Liga o controle remoto e outros acessórios sem fio. | O controle remoto pararia de funcionar. | - | `com.android.bluetooth` |
| **Bluetooth da Xiaomi** | Manter (necessário) | Liga o controle remoto Xiaomi (inclusive o botão de ligar). | O controle remoto poderia parar. | - | `com.mi.bluetooth` |
| **Busca nas Configurações** | Manter (necessário) | Permite pesquisar opções dentro do menu Configurações. | Sem ganho real; mantenha. | - | `com.android.settings.intelligence` |
| **Canais da tela inicial** | Manter (necessário) | Guarda os canais e programas que aparecem nas linhas da tela inicial. | A tela inicial ficaria vazia ou com erros. | - | `com.android.providers.tv` |
| **Certificados de segurança** | Manter (necessário) | Guarda certificados usados em conexões seguras. | Logins e conexões seguras poderiam falhar. | - | `com.android.keychain` |
| **Chromecast integrado** | Manter (necessário) | Permite transmitir do celular para a TV. | Você perderia o Chromecast. | - | `com.google.android.apps.mediashell` |
| **Componente de compatibilidade** | Manter (necessário) | Peça técnica exigida pelo Google; fica inativa. | Sem ganho; mantenha. | - | `com.android.cts.ctsshim` |
| **Componente de compatibilidade** | Manter (necessário) | Peça técnica exigida pelo Google; fica inativa. | Sem ganho; mantenha. | - | `com.android.cts.priv.ctsshim` |
| **Configuração de parceiro** | Manter (necessário) | Ajustes do fabricante no primeiro uso. | Sem ganho real; mantenha. | - | `com.google.android.partnersetup` |
| **Configurações da TV** | Manter (necessário) | O menu de Configurações (engrenagem). | Você perderia acesso às configurações. | - | `com.android.tv.settings` |
| **Confirmação de backup** | Manter (necessário) | Janela de confirmação de backup/restauração. | Sem ganho real; mantenha. | - | `com.android.backupconfirm` |
| **Controle de permissões** | Manter (necessário) | Pergunta e guarda as permissões dos apps. | Apps poderiam parar de funcionar. | - | `com.android.permissioncontroller` |
| **Controle de permissões** | Manter (necessário) | Pergunta e guarda as permissões dos apps. | Apps poderiam parar de funcionar. | - | `com.google.android.permissioncontroller` |
| **Controle pelo celular** | Manter (necessário) | Permite usar o app Google TV do celular como controle. | O celular não controlaria mais a TV. | - | `com.google.android.tv.remote.service` |
| **Dados dos módulos do sistema** | Manter (necessário) | Informações sobre as atualizações do sistema. | Atualizações poderiam falhar. | - | `com.google.android.modulemetadata` |
| **Disney+** | Manter (necessário) | App do Disney+. | Protegido (streaming). | - | `com.disney.disneyplus` |
| **Elemento seguro** | Manter (necessário) | Guarda chaves de segurança do sistema. | Recursos de segurança poderiam falhar. | - | `com.android.se` |
| **Entradas de vídeo (Amlogic)** | Manter (necessário) | Parte do sistema de vídeo do processador. | Imagem poderia falhar. | - | `com.droidlogic.tvinput` |
| **Envio de relatórios de erro** | Manter (necessário) | Envia relatórios de erro ao Google. | Nada perceptível. | Muito baixo | `com.google.android.tv.bugreportsender` |
| **Gerenciador de downloads** | Manter (necessário) | Baixa arquivos para os apps (inclusive atualizações). | Downloads e atualizações falhariam. | - | `com.android.providers.downloads` |
| **Globoplay** | Manter (necessário) | App do Globoplay. | Protegido (streaming). | - | `com.globo.globotv` |
| **Google Play Services** | Manter (necessário) | Conta Google, proteção de vídeo (DRM), Chromecast e atualizações. | Netflix, YouTube e login parariam. | Alto, mas necessário | `com.google.android.gms` |
| **Inicialização única** | Manter (necessário) | Roda só na primeira vez que a TV liga. | Sem ganho real; mantenha. | - | `com.google.android.onetimeinitializer` |
| **Instalador de apps** | Manter (necessário) | Instala e atualiza aplicativos. | Não seria possível instalar/atualizar apps. | - | `com.android.packageinstaller` |
| **Instalador de apps** | Manter (necessário) | Instala e atualiza aplicativos. | Não seria possível instalar/atualizar apps. | - | `com.google.android.packageinstaller` |
| **Instalador de certificados** | Manter (necessário) | Instala certificados de segurança. | Sem ganho real; mantenha. | - | `com.android.certinstaller` |
| **Interface do sistema** | Manter (necessário) | Mostra avisos, barra de volume e janelas do sistema na tela. | A TV ficaria inutilizável. | - | `com.android.systemui` |
| **Localização do sistema** | Manter (necessário) | Informa a região aproximada para apps (ex.: catálogo do país). | Apps poderiam mostrar conteúdo da região errada. | - | `com.android.location.fused` |
| **Max** | Manter (necessário) | App do Max. | Protegido (streaming). | - | `com.wbd.stream` |
| **Netflix** | Manter (necessário) | App da Netflix. | Protegido (streaming). | - | `com.netflix.ninja` |
| **Pareamento de acessórios** | Manter (necessário) | Ajuda a parear acessórios. | Pareamentos poderiam falhar. | - | `com.android.companiondevicemanager` |
| **Personalização da Xiaomi** | Manter (necessário) | Ajustes do fabricante (fica sempre ativo). | Funções do aparelho poderiam falhar. | - | `com.xiaomi.android.tvsetup.partnercustomizer` |
| **Pilha de rede** | Manter (necessário) | Faz a conexão de rede funcionar. | A TV perderia a internet. | - | `com.android.networkstack` |
| **Pilha de rede** | Manter (necessário) | Faz a conexão de rede funcionar. | A TV perderia a internet. | - | `com.google.android.networkstack` |
| **Play Store** | Manter (necessário) | Loja de apps; também atualiza Netflix, YouTube etc. | Seus apps deixariam de ser atualizados. | - | `com.android.vending` |
| **Prime Video** | Manter (necessário) | App do Prime Video. | Protegido (streaming). | - | `com.amazon.amazonvideo.livingroom` |
| **Protetor de tela básico** | Manter (necessário) | Protetor de tela padrão do Android. | A TV poderia ficar sem protetor de tela. | - | `com.android.dreams.basic` |
| **Proxy de rede** | Manter (necessário) | Suporte a proxy de internet. | Sem ganho real; mantenha. | - | `com.android.proxyhandler` |
| **Recursos do Wi-Fi** | Manter (necessário) | Configurações internas do Wi-Fi. | O Wi-Fi poderia falhar. | - | `com.android.wifi.resources` |
| **Seletor de arquivos** | Manter (necessário) | Janela para escolher arquivos dentro de apps. | Apps não conseguiriam abrir arquivos. | - | `com.android.documentsui` |
| **Serviço de TV da Xiaomi** | Manter (necessário) | Funções de sistema da Xiaomi para a TV. | Funções do aparelho poderiam falhar. | - | `xiaomi.tvservice` |
| **Serviços do Google** | Manter (necessário) | Processo dos serviços do Google. | Apps do Google parariam. | - | `com.google.process.gservices` |
| **Serviços do Google (conta)** | Manter (necessário) | Liga a TV à sua conta Google. | Apps do Google e a Play Store parariam. | - | `com.google.android.gsf` |
| **Serviços internos do Android** | Manter (necessário) | Funções internas do sistema (notificações, etc.). | O sistema poderia falhar. | - | `com.google.android.ext.services` |
| **Shell do sistema** | Manter (necessário) | Usado pelo ADB, inclusive por este programa. | Este programa deixaria de funcionar. | - | `com.android.shell` |
| **Sistema Android (núcleo)** | Manter (necessário) | O próprio sistema operacional. | A TV não funcionaria. | - | `android` |
| **Sistema do chip Amlogic** | Manter (necessário) | Controla vídeo, HDMI e áudio do processador. | Imagem ou som poderiam parar. | - | `com.droidlogic` |
| **Spotify** | Manter (necessário) | App do Spotify. | Protegido (streaming). | - | `com.spotify.tv.android` |
| **Teclado na tela (Gboard)** | Manter (necessário) | Teclado que aparece para digitar senhas e buscas. | Você não conseguiria digitar. | - | `com.google.android.inputmethod.latin` |
| **Teclados e controles** | Manter (necessário) | Define o layout de teclados e controles conectados. | Teclas poderiam funcionar errado. | - | `com.android.inputdevices` |
| **Tela inicial do Google** | Manter (necessário) | A tela principal da TV, com as linhas de apps e canais. | A TV ficaria sem tela inicial. | Alto (~250 MB), mas necessário | `com.google.android.tvlauncher` |
| **Tela inicial do Google TV** | Manter (necessário) | A tela principal (firmwares mais novos). | A TV ficaria sem tela inicial. | - | `com.google.android.apps.tv.launcherx` |
| **Transferência USB** | Manter (necessário) | Troca de arquivos pelo cabo USB. | Sem ganho real; mantenha. | - | `com.android.mtp` |
| **Verificação de links** | Manter (necessário) | Decide qual app abre cada link. | Links poderiam abrir no app errado. | - | `com.android.statementservice` |
| **Voz do sistema** | Manter (necessário) | Converte texto em fala (acessibilidade). | Sem ganho real; mantenha. | - | `com.google.android.tts` |
| **WebView** | Manter (necessário) | Mostra páginas da internet dentro de apps (logins, termos). | Telas de login de vários apps quebrariam. | - | `com.android.webview` |
| **WebView** | Manter (necessário) | Mostra páginas da internet dentro de apps (logins, termos). | Telas de login de vários apps quebrariam. | - | `com.google.android.webview` |
| **YouTube** | Manter (necessário) | App do YouTube. | Protegido (streaming). | - | `com.google.android.youtube.tv` |

## Apps que não estão na lista

O programa reconhece a família pelo começo do nome técnico:

| Começo do nome | Explicação mostrada | Recomendação |
|---|---|---|
| `com.google.android.overlay…` | Ajuste do sistema (overlay): Pequeno ajuste de aparência ou configuração do sistema. | Manter (necessário) |
| `com.android.overlay…` | Ajuste do sistema (overlay): Pequeno ajuste de aparência ou configuração do sistema. | Manter (necessário) |
| contém `.overlay` | Ajuste do sistema (overlay): Pequeno ajuste de aparência ou configuração do sistema. | Manter (necessário) |
| contém `.resources` | Recursos de um componente do sistema: Textos e imagens usados por uma parte do sistema. | Manter (necessário) |
| `com.android.providers.…` | Banco de dados do sistema: Guarda dados usados pelo sistema e pelos apps. | Manter (necessário) |
| `com.droidlogic…` | Componente do chip Amlogic: Parte do sistema de vídeo, áudio ou HDMI do processador. | Manter (necessário) |
| `com.amlogic…` | Componente do chip Amlogic: Parte do sistema de vídeo, áudio ou HDMI do processador. | Manter (necessário) |
| `com.google.android.gms…` | Parte do Google Play Services: Componente dos serviços do Google. | Manter (necessário) |
| `com.google.android.tv.…` | Componente do Android TV (Google): Parte do sistema Android TV. | Manter (necessário) |
| `com.android.tv.…` | Componente do Android TV: Parte do sistema Android TV. | Manter (necessário) |
| `com.xiaomi.…` | Componente da Xiaomi: Software do fabricante (Xiaomi). Função exata não identificada. | Não mexer (sem informação) |
| `com.mitv.…` | Componente Xiaomi Mi TV: Software do fabricante (Xiaomi). Função exata não identificada. | Não mexer (sem informação) |
| `com.miui.…` | Componente da Xiaomi (MIUI): Software do fabricante (Xiaomi). Função exata não identificada. | Não mexer (sem informação) |
| `com.mi.…` | Componente da Xiaomi: Software do fabricante (Xiaomi). Função exata não identificada. | Não mexer (sem informação) |
| `com.android.…` | Componente do Android: Parte do sistema Android. | Não mexer (sem informação) |
| `com.google.…` | Componente do Google: Software do Google instalado de fábrica. | Não mexer (sem informação) |

## Animações

| Ajuste | Padrão | Sugestão | Efeito | Reversão |
|---|---|---|---|---|
| Escalas de animação (janela, transição, duração) | 1× | 0,5× | Menus mais ágeis; não afeta vídeo | Voltar para 1× (o valor anterior fica no histórico) |

## Ganho esperado (realista)

Desativar apps ociosos libera dezenas a pouco mais de cem MB de RAM e reduz a atividade em segundo plano. Isso **não** transforma o hardware: o Mi TV Stick 4K usa núcleos Cortex-A35, de baixo desempenho.

A melhora que mais se sente costuma vir de:
1. manter **pelo menos 1 GB livre** de armazenamento;
2. reduzir as animações;
3. usar Wi-Fi de **5 GHz**: o Wi-Fi e o Bluetooth do controle dividem o mesmo chip.
