# 🙏 MeditacaoBot Diário - IASD de Angra do Heroísmo ✨

Um bot automatizado e resiliente para extrair meditações diárias do site CPB Mais e publicá-las de forma independente e agendada num canal do **Telegram** e num grupo/comunidade do **WhatsApp**. Nunca mais se esqueça de partilhar a mensagem do dia!

## 🎯 Sobre o Projeto

Este projeto foi criado para automatizar a tarefa diária de copiar, formatar e colar as meditações matinais, da mulher e dos jovens. O bot elimina o trabalho manual: acede ao site oficial, extrai o conteúdo, trata as particularidades de formatação de cada plataforma e distribui as mensagens de forma limpa, garantindo uma experiência de leitura agradável e profissional para a comunidade da igreja.

## 🚀 Funcionalidades Principais

* **Scraping Automatizado Multi-Fonte:** Recolhe diariamente três vertentes de conteúdo:
    * Meditação Matinal
    * Meditação da Mulher
    * Meditação Jovem
* **Publicação Segmentada e Individual:** No WhatsApp, cada meditação é enviada como uma publicação isolada no chat, evitando blocos massivos de texto.
* **Tratamento Inteligente de Markdown:** Adapta dinamicamente o texto para cada plataforma. Remove automaticamente barras de escape (`\`) e formatações conflituosas para que o texto fique limpo tanto no Telegram como no WhatsApp.
* **Thumbnails Expandidos do YouTube:** O motor do WhatsApp aguarda **10 segundos** obrigatórios entre o envio de cada meditação, dando tempo ao servidor para carregar e expandir a pré-visualização visual (thumbnail) dos vídeos do YouTube.
* **Gestão Horária Automática (Fuso Horário dos Açores):** Graças a uma verificação lógica integrada, o sistema deteta mudanças de horário e executa sempre às **07:00 da manhã locais em Angra do Heroísmo**, quer estejamos no Horário de Verão (UTC+0) ou no Horário de Inverno (UTC-1).
* **Persistência de Sessão sem Custos:** Utiliza emulação headless (WhatsApp Web) guardada de forma encriptada através de *Artifacts* do GitHub Actions, contornando as restrições e custos da API Business oficial da Meta.

## 🔧 Como Funciona

1. **Raspagem e Telegram (Python):** O script `meditacao_iasdah.py` acede ao HTML com `requests` e `BeautifulSoup4`, extrai os dados, envia-os para a API do Telegram e salva o payload estruturado num ficheiro local com delimitadores de corte.
2. **Envio Resiliente para o WhatsApp (Node.js):** O script `send_whatsapp.js` inicializa um navegador Chromium invisível através de `puppeteer`, carrega os tokens criptográficos de login guardados anteriormente, isola as mensagens, limpa caracteres inválidos e injeta-as diretamente no Chat ID nativo da Comunidade.

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
```bash
name: Publicar Meditação Diária no Telegram e WhatsApp

on:
  schedule:
    # Acorda às 07:00 UTC todos os dias. 
    - cron: '0 7 * * *'
  workflow_dispatch: # Permite disparo manual a qualquer momento

jobs:
  build-and-send:
    runs-on: ubuntu-latest
    steps:
      - name: Check out a cópia do repositório
        uses: actions/checkout@v3

      - name: Configurar o Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Instalar o locale de Português Europeu (pt_PT)
        run: |
          sudo apt-get update
          sudo apt-get install -y language-pack-pt
          sudo locale-gen pt_PT.UTF-8
          sudo update-locale LANG=pt_PT.UTF-8

      - name: Ajustar Horário Local dos Açores (Verão/Inverno)
        run: |
          echo "A verificar mudança de hora local para Atlantic/Azores..."
          TZ="Atlantic/Azores" TZ_OFFSET=$(date +%z)
          echo "Desvio atual detetado: $TZ_OFFSET"
          if [ "$TZ_OFFSET" = "-0100" ]; then
            echo "Detectado: Horário de Inverno nos Açores!"
            echo "A adiar a execução em 60 minutos para publicar às 07:00 locais."
            sleep 3600
          else
            echo "Detectado: Horário de Verão nos Açores. A avançar imediatamente."
          fi

      - name: Configurar o Node.js Environment
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Restaurar o Estado da Sessão do WhatsApp
        uses: dawidd6/action-download-artifact@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          workflow: meditacao_diaria.yml
          name: whatsapp-session
          path: whatsapp_auth
          if_no_artifact_found: warn

      - name: Instalar dependências (Python & Node.js)
        run: |
          python -m pip install --upgrade pip
          pip install requests beautifulsoup4 urllib3
          npm install whatsapp-web.js qrcode-terminal

      - name: Executar o script de publicação (Scraping & Telegram)
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          EMAIL_ADDRESS: ${{ secrets.EMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
        run: python meditacao_iasdah.py

      - name: Executar envio automatizado para o WhatsApp
        env:
          WHATSAPP_GROUP_ID: ${{ secrets.WHATSAPP_GROUP_ID }}
        run: node send_whatsapp.js

      - name: Interceptar e Tratar Alerta de Sessão Expirada
        if: failure()
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_PERSONAL_CHAT_ID: ${{ secrets.TELEGRAM_PERSONAL_CHAT_ID }}
        run: python alert_failure.py

      - name: Guardar Estado Atualizado da Sessão do WhatsApp
        if: success()
        uses: actions/upload-artifact@v4
        with:
          name: whatsapp-session
          path: whatsapp_auth
          retention-days: 2
          overwrite: true
          include-hidden-files: true
```
## 🔐 Primeira Execução e Vinculação (QR Code)

No primeiríssimo arranque (ou caso a sessão seja revogada), o robô necessita de uma autenticação inicial:

1. Vá ao separador Actions no seu repositório GitHub.
2. Selecione o workflow e clique em Run workflow manualmente.
3. Abra os logs em tempo real no passo Executar envio automatizado para o WhatsApp.
4. O script detetará a ausência de sessão e desenhará um QR Code em bloco invertido com alto contraste diretamente no terminal.
5. Abra o WhatsApp no seu telemóvel, vai a Dispositivos Associados > Associar um dispositivo e faça o scan do ecrã.
6. O sistema validará a ligação, enviará as meditações e trancará os arquivos de sessão na nuvem de forma persistente. Não precisará de repetir o processo a menos que desconecte explicitamente o dispositivo.

E pronto! O seu MeditaBot Diário híbrido está configurado, testado e pronto para abençoar a comunidade e a igreja de Angra do Heroísmo em ambas as plataformas de forma 100% automática. 🎉
