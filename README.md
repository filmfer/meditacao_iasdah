🙏 MeditaBot Diário ✨
Um bot simples e eficaz para extrair meditações diárias do site CPB Mais e publicá-las automaticamente num grupo do Telegram. Nunca mais se esqueça de partilhar a mensagem do dia!

🎯 Sobre o Projeto
Este projeto foi criado para automatizar a tarefa diária de copiar e colar as meditações matinais, da mulher e dos jovens. O bot faz todo o trabalho pesado: acede ao site, extrai o conteúdo relevante, formata-o de maneira elegante e envia para um grupo do Telegram à hora agendada.

🚀 Funcionalidades Principais
Scraping Automatizado: Extrai dados de múltiplas fontes de meditação:

Meditação Matinal

Meditação da Mulher

Meditação Jovem

Formatação Inteligente: A mensagem é formatada com Markdown para uma leitura agradável no Telegram (negrito, itálico, etc.).

Conteúdo Completo: Publica o título do dia, o verso bíblico, o texto completo da meditação e o link do vídeo do YouTube associado.

Publicação no Telegram: Utiliza a API oficial de Bots do Telegram para uma publicação segura e fiável.

Agendamento Fácil: Desenhado para ser executado diariamente através de agendadores como o GitHub Actions ou Cron.

🔧 Como Funciona
O fluxo do bot é bastante simples:

Aceder ao Site: Usa a biblioteca requests para obter o HTML da página principal das meditações.

Encontrar o Link do Dia: Analisa o HTML com o BeautifulSoup para encontrar o link que leva à meditação do dia corrente.

Extrair o Conteúdo: Acede à página da meditação diária e extrai cada parte do conteúdo (título, verso, texto, link do YouTube).

Montar e Enviar: Formata todo o conteúdo numa única mensagem e envia para o chat especificado no Telegram através de um pedido à API do Telegram.

⚙️ Instalação e Configuração
Siga estes passos para colocar o seu bot a funcionar.

1. Pré-requisitos
Python 3.7 ou superior instalado.

Uma conta no Telegram.

2. Clonar o Repositório
Bash

git clone [URL_DO_SEU_REPOSITÓRIO_GIT]
cd [NOME_DA_PASTA_DO_REPOSITÓRIO]
3. Criar e Instalar Dependências
Crie um ficheiro chamado requirements.txt com o seguinte conteúdo:

Plaintext

requests
beautifulsoup4
urllib3
Agora, instale estas dependências:

Bash

pip install -r requirements.txt
4. 🔑 Obter as Credenciais do Telegram
Para o bot funcionar, precisa de duas informações secretas:

Token do Bot (TELEGRAM_BOT_TOKEN):

No Telegram, fale com o @BotFather.

Envie /newbot e siga as instruções para criar o seu bot.

O BotFather irá fornecer-lhe um token. Guarde-o!

ID do Chat (TELEGRAM_CHAT_ID):

Adicione o seu novo bot ao grupo do Telegram onde quer que as mensagens sejam publicadas.

Envie uma mensagem qualquer no grupo.

Aceda ao seguinte URL no seu navegador, substituindo <SEU_TOKEN>:
https://api.telegram.org/bot<SEU_TOKEN>/getUpdates

Procure pelo ID do chat (geralmente um número negativo, como -100123456789).

5. Configurar as Variáveis de Ambiente
Por segurança, não coloque as suas credenciais diretamente no código. Em vez disso, o script lê a partir de variáveis de ambiente.

No Linux ou macOS:

Bash

export TELEGRAM_BOT_TOKEN="O_SEU_TOKEN_AQUI"
export TELEGRAM_CHAT_ID="O_SEU_ID_DO_CHAT_AQUI"
No Windows (Command Prompt):

Bash

set TELEGRAM_BOT_TOKEN="O_SEU_TOKEN_AQUI"
set TELEGRAM_CHAT_ID="O_SEU_ID_DO_CHAT_AQUI"
▶️ Executar o Bot Manualmente
Depois de configurar as variáveis de ambiente, pode testar o script executando-o diretamente no seu terminal:

Bash

python seu_script.py # Substitua pelo nome do seu ficheiro .py
🗓️ Agendamento Automático com GitHub Actions
Esta é a forma recomendada para garantir que o seu bot publica todos os dias às 7:30 da manhã.

Crie a Estrutura: No seu repositório, crie a pasta .github/workflows/.

Crie o Ficheiro de Workflow: Dentro dessa pasta, crie um ficheiro daily_post.yml com o seguinte conteúdo:

YAML

name: Publicar Meditação Diária no Telegram

on:
  schedule:
    # Executa às 7:30 UTC. Nos Açores, em agosto (UTC+0), isto corresponde às 7:30 locais.
    # Ajuste conforme necessário para o fuso horário de inverno.
    - cron: '30 7 * * *'
  workflow_dispatch:

jobs:
  build-and-send:
    runs-on: ubuntu-latest
    steps:
      - name: Check out do código
        uses: actions/checkout@v3

      - name: Configurar Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Instalar dependências
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Executar o script de publicação
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python seu_script.py # <-- SUBSTITUA PELO NOME DO SEU FICHEIRO
Adicione os Secrets ao GitHub:

No seu repositório no GitHub, vá a Settings > Secrets and variables > Actions.

Clique em New repository secret.

Crie um secret chamado TELEGRAM_BOT_TOKEN e cole o seu token.
Crie outro secret chamado TELEGRAM_CHAT_ID e cole o ID do seu grupo.

E pronto! O seu MeditaBot Diário está configurado para abençoar o seu grupo do Telegram todos os dias. 🎉
