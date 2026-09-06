# 🙏 MeditacaoBot Diário - IASD de Angra do Heroísmo ✨

Um bot automatizado e resiliente para extrair meditações diárias do site CPB Mais e publicá-las de forma independente e agendada num canal do **Telegram** e num grupo/comunidade do **WhatsApp**. Nunca mais se esqueça de partilhar a mensagem do dia!

## 🎯 Sobre o Projeto

Este projeto foi criado para automatizar a tarefa diária de copiar, formatar e colar as meditações matinais, da mulher e dos jovens. O bot elimina o trabalho manual: acede ao site oficial, extrai o conteúdo, trata as particularidades de formatação de cada plataforma e distribui as mensagens de forma limpa, garantindo uma experiência de leitura agradável e profissional para a comunidade da igreja.

## 🚀 Funcionalidades Principais

* **Scraping Automatizado Multi-Fonte:** Recolhe diariamente três vertentes de conteúdo:
    * Meditação Matinal
    * Meditação da Mulher
    * Meditação Jovem
* **Publicação em Mensagem Única (imagem + texto):** No WhatsApp, cada meditação sai como **uma única mensagem**: primeiro aparece a miniatura do vídeo do YouTube e, por baixo (na *caption*), o título, o texto e os links finais. Se o texto exceder o limite de caption do WhatsApp (~1024 caracteres), é enviado apenas o texto — o link do YouTube já faz parte dele. Nunca se trunca texto nem se publica a imagem sozinha.
* **Tratamento Inteligente de Markdown:** Adapta dinamicamente o texto para cada plataforma. Remove automaticamente barras de escape (`\`) e formatações conflituosas para que o texto fique limpo tanto no Telegram como no WhatsApp.
* **Miniatura do YouTube Garantida:** A miniatura é descarregada de forma determinística de `img.youtube.com` (tenta `maxresdefault`, com fallback para `hqdefault` e deteção do placeholder vazio) e enviada como imagem real na mensagem — contornando a instabilidade do preview de links do WhatsApp. Falhas aqui são não-fatais (envia só o texto).
* **Publicação a Qualquer Hora, Uma Vez por Dia:** Sem janela horária obrigatória — o run publica de imediato, à hora a que arranca. Três disparos cron redundantes funcionam como retry automático; a **deduplicação diária** (via API de workflow runs) garante no máximo uma publicação por dia. Um run só começa quando o anterior termina (concorrência serializada).
* **Autenticação Resiliente (fábrica de clientes):** Até **3 tentativas de 90s**, cada uma com um `Client` novo — nunca se re-inicializa uma instância destruída (evita o crash `Target closed`) — com watchdog por tentativa e `initialize()` sempre capturado. O `webVersionCache` está pinado à versão *current* do WhatsApp Web, com instruções de manutenção no código.
* **Modo de Pareamento (`WHATSAPP_PAREAMENTO=1`):** Executa apenas a autenticação — desenha o QR no terminal, guarda a sessão em `./whatsapp_auth` e sai; não exige payload nem ID de grupo. Ideal para religar o bot quando o artefacto da sessão se perde.
* **Persistência de Sessão sem Custos:** Utiliza emulação headless (WhatsApp Web) guardada de forma encriptada através de *Artifacts* do GitHub Actions (retenção de 90 dias, com overwrite), contornando as restrições e custos da API Business oficial da Meta.
* **Alertas de Falha Multi-Canal:** Falhas de scraping, envio ou autenticação disparam e-mail (Gmail) e alerta imediato no Telegram pessoal (`alert_failure.py`), com instruções de ação.

## 🔧 Como Funciona

1. **Raspagem e Telegram (Python — `meditacao_iasdah.py`):** Acede ao HTML com `requests` e `BeautifulSoup4` (com 3 tentativas por fonte), extrai as três meditações, envia-as para o Telegram e escreve o payload limpo (sem escapes MarkdownV2) em `whatsapp_msg.txt`, com as meditações separadas por delimitadores `===DIVISAO_MEDITACAO===`.

2. **Envio para o WhatsApp (Node.js — `send_whatsapp.js`):** Organizado em duas fases:
   * **`autenticar()`** — fábrica de clientes: cada tentativa cria um `Client` novo (LocalAuth + `webVersionCache` pinado à versão current do WhatsApp Web), com watchdog de 90s e até 3 tentativas. Se a sessão guardada for válida, entra direto (`ready`); se não, desenha um QR Code no terminal com janela de 5 minutos para o scan. Erros de `initialize()` são sempre capturados e não crasham o processo.
   * **`executarEnvio(client)`** — lê o payload, isola cada meditação, descarrega a miniatura do vídeo e publica **uma mensagem única por meditação** (imagem primeiro, texto na caption). Termina com a mensagem de motivação aleatória e um encerramento controlado com esperas que garantem a entrega real da última mensagem.

## ⚙️ Instalação e Configuração

### Pré-requisitos
* Python 3.10 ou superior instalado.
* Node.js v18 ou superior instalado.
* Uma conta ativa no Telegram e no WhatsApp.

### Clonar o Repositório
```bash
git clone [URL_DO_SEU_REPOSITÓRIO_GIT]
cd [NOME_DA_PASTA_DO_REPOSITÓRIO]
```
### Configurar Dependências de Sistema
Certifique-se de que o seu ambiente local possui as dependências necessárias instaladas:

Python (pip):
```bash
pip install requests beautifulsoup4 urllib3
```

### Node.js (npm):
```bash
npm install whatsapp-web.js qrcode-terminal
```

## 🔑 Configuração das Variáveis Secretas (GitHub Secrets)
Para que a automação seja executada na nuvem de forma segura, deve configurar os seguintes Secrets nas definições do seu repositório do GitHub (`Settings > Secrets and variables > Actions`):

| Nome do Secret | Descrição / Origem |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Token numérico longo fornecido pelo `@BotFather` ao criar o bot. |
| `TELEGRAM_CHAT_ID` | ID numérico do grupo/canal do Telegram (ex: `-100XXXXXXXXXX`). |
| `WHATSAPP_GROUP_ID` | ID nativo de infraestrutura do grupo da Comunidade (ex: `1203630XXXXXXXXX@g.us`). |
| `TELEGRAM_PERSONAL_CHAT_ID` | O seu ID pessoal (via `@userinfobot`) para receber alertas imediatos caso a sessão do WhatsApp caia. |
| `EMAIL_ADDRESS` | O seu endereço de e-mail para logs de erro alternativos. |
| `GMAIL_APP_PASSWORD` | Password de aplicação gerada na sua conta Google para envio de e-mails de alerta. |

## 🗓️ Automação com GitHub Actions
O fluxo está totalmente automatizado para acordar todas as manhãs na nuvem do GitHub. O ficheiro de configuração do workflow encontra-se em .github/workflows/meditacao_diaria.yml e possui a seguinte estrutura de produção:
```yaml
name: Publicar Meditação Diária no Telegram e WhatsApp

on:
  schedule:
    # A publicação corre de imediato, a qualquer hora (não há janela 07:00-08:00).
    # Três disparos redundantes contra atrasos do scheduler do GitHub;
    # a deduplicação diária garante que só o primeiro publica.
    - cron: '0 5 * * *'    # disparo principal (UTC)
    - cron: '30 6 * * *'   # redundância
    - cron: '15 8 * * *'   # sentinela: publica com atraso se os anteriores falharem
  workflow_dispatch:
    inputs:
      force:
        description: 'Ignorar a verificação de duplicação diária e publicar na mesma'
        type: boolean
        required: false
        default: false

permissions:
  contents: read   # mínimo necessário
  actions: read    # deduplicação via API + descarregar artefactos

concurrency:
  group: meditacao-diaria   # serializa runs: nunca há duas publicações em paralelo
  cancel-in-progress: false
```

**Sequência de steps** (fonte completa em `.github/workflows/meditacao_diaria.yml`):

1. **Deduplicação diária** — consulta a API de workflow runs e salta a execução se já existir publicação de hoje concluída com sucesso ou ainda em curso (bypass manual com `force`). Em erro da API, falha aberta: é pior ficar um dia sem meditação do que arriscar um duplicado.
2. **Diagnóstico de horário** — registra no log a hora em UTC, no runner e nos Açores.
3. **Ambiente** — Python 3.10, Node.js 22, locale `pt_PT.UTF-8`.
4. **Restaurar a sessão WhatsApp** — descarrega o artefacto `whatsapp-session` do último run (`if_no_artifact_found: warn`).
5. **Dependências** — `pip install requests beautifulsoup4 urllib3` + `npm install whatsapp-web.js@1.34.7 qrcode-terminal`.
6. **Scraping & Telegram** — `python meditacao_iasdah.py`.
7. **Envio WhatsApp** — `node send_whatsapp.js` (com `WHATSAPP_GROUP_ID`).
8. **Alerta de falha** — `python alert_failure.py` (apenas em `failure()`) envia alerta imediato para o Telegram pessoal.
9. **Limpeza + upload da sessão** — remove os ficheiros `Singleton*` e republica o artefacto `whatsapp-session` (`overwrite: true`, retenção de 90 dias) para o dia seguinte.
## 🔐 Primeira Execução e Vinculação (QR Code)

No primeiro arranque — ou se a sessão for perdida/revogada — o robô precisa de nova autenticação. Há duas formas:

### No GitHub Actions (recomendado — recria o artefacto da sessão)

1. Vá ao separador **Actions** do repositório e clique em **Run workflow** (disparo manual).
2. Abra os logs em tempo real do passo **Executar envio automatizado para o WhatsApp**.
3. O script deteta a ausência de sessão e desenha um QR Code invertido e de alto contraste no log — com janela de **5 minutos** para o scan (o QR é redesenhado se refrescar).
4. Abra o WhatsApp no telemóvel: **Definições > Dispositivos ligados > Ligar um dispositivo** e aponte para o QR.
5. Autenticado, o sistema envia as meditações e **republica a sessão como artefacto** para os dias seguintes. Não repetirá o processo a menos que desconecte explicitamente o dispositivo.

### No terminal local (modo de pareamento)

```bash
WHATSAPP_PAREAMENTO=1 node send_whatsapp.js
```

Executa apenas a autenticação: desenha o QR, guarda a sessão em `./whatsapp_auth` e sai — não exige `whatsapp_msg.txt` nem `WHATSAPP_GROUP_ID`. Útil para testes rápidos; note que a sessão fica no seu computador (o bot na nuvem usa o artefacto do Actions).

## 🛠️ Manutenção

* **Pin do `webVersionCache`:** está fixado à versão `2.3000.1046922887-alpha` (current em setembro/2026), que **expira a 2026-11-06**. Se voltar a ver "nem `qr` nem `ready`" nos logs — mesmo após os 3 retries automáticos — actualize o `remotePath` em `send_whatsapp.js` com a versão *current* listada em https://wppconnect.io/whatsapp-versions.
* **Artefacto da sessão:** o step de upload corre com `overwrite: true` em `always()` — um run que falhe **antes** de autenticar pode sobrescrever a sessão boa por uma quebrada. Se suspeitar disso, re-ligue o dispositivo via QR (a nova sessão é republicada automaticamente).
* **Dependências:** `whatsapp-web.js` está fixado a `1.34.7` no workflow e em `package.json` — actualize com cuidado e teste em modo de pareamento antes de deixar em produção.

E pronto! O seu MeditaBot Diário híbrido está configurado, testado e pronto para abençoar a comunidade e a igreja de Angra do Heroísmo em ambas as plataformas de forma 100% automática. 🎉
