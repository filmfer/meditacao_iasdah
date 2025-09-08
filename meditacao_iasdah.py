import requests
import os
from bs4 import BeautifulSoup
import datetime
import locale
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suprime avisos de SSL explicitamente
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

def safe_locale_set():
    """Tenta definir o locale para Português de Portugal de forma segura."""
    try:
        # Prioridade para o formato padrão em sistemas Linux/macOS
        locale.setlocale(locale.LC_TIME, 'pt_PT.UTF-8')
    except locale.Error:
        try:
            # Fallback para sistemas Windows
            locale.setlocale(locale.LC_TIME, 'Portuguese_Portugal.1252')
        except locale.Error:
            print("Aviso: Não foi possível definir o locale para pt_PT. A data pode aparecer em inglês.")
            pass

def scrape_meditation(base_url, meditacao_matinal_title):
    """Faz o scraping da página da meditação e retorna o texto formatado."""
    try:
        response = requests.get(base_url, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Encontra o link para a meditação diária
        link_tag = soup.find("a", class_="mdl-button mdl-button--colored mdl-js-button mdl-js-ripple-effect")
        if not link_tag or not link_tag.has_attr("href"):
            return f"Link da meditação diária não encontrado para {base_url}"

        meditation_url = link_tag["href"]

        # Faz o scraping da página da meditação diária
        response = requests.get(meditation_url, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Extrai e formata as informações
        meditacao_matinal = f"*{meditacao_matinal_title}*"

        safe_locale_set()
        today = datetime.date.today()
        weekday = today.strftime("%A").capitalize()
        day = today.strftime("%d")
        month = today.strftime("%B").capitalize()
        weekday_date = f"{weekday}, {day} de {month}"

        title_tag = soup.find("div", class_="mdl-typography--headline")
        title = title_tag.text.strip() if title_tag else "Título não encontrado"
        title_text = f"*{title}*"

        reference_text_tag = soup.find("div", class_="descriptionText versoBiblico")
        reference_text = reference_text_tag.text.strip() if reference_text_tag else "Verso não encontrado"
        reference_text_content = f"_{reference_text}_"

        meditation_content_tag = soup.find("div", class_="conteudoMeditacao")
        meditation_content = meditation_content_tag.text.strip() if meditation_content_tag else "Conteúdo não encontrado"

        youtube_iframe_tag = soup.find("iframe", {"src": lambda src: src and "youtube.com/embed" in src})
        youtube_link = youtube_iframe_tag["src"].split('?')[0].replace("embed/", "watch?v=") if youtube_iframe_tag else ""

        # Formata a mensagem final (com o link do YouTube na linha seguinte, se existir)
        formatted_text = (
            f"{meditacao_matinal}\n"
            f"{weekday_date}\n\n"
            f"{title_text}\n"
            f"{reference_text_content}\n\n"
            f"{meditation_content}\n\n"
            f"{youtube_link}"
        )

        return formatted_text.strip()

    except requests.exceptions.RequestException as e:
        return f"Erro de Request para {base_url}: {e}"
    except Exception as e:
        return f"Erro inesperado para {base_url}: {e}"

def send_telegram_message(text, bot_token, chat_id):
    """Envia uma mensagem de texto para um chat do Telegram usando a API do Bot."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
       # O Telegram suporta Markdown para formatação de *negrito* e _itálico_
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"Mensagem enviada com sucesso para o Telegram (Chat ID: {chat_id})")
    except requests.exceptions.RequestException as e:
        print(f"Falha ao enviar mensagem para o Telegram: {e}")
        print(f"Resposta da API: {response.text}")


if __name__ == "__main__":
    # Carrega as credenciais do Telegram a partir de variáveis de ambiente
    # É mais seguro do que colocar diretamente no código
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("As variáveis de ambiente TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID não foram definidas.")
    else:
        meditation_sources = [
            ("https://mais.cpb.com.br/meditacoes-diarias/", "Meditação Matinal"),
            ("https://mais.cpb.com.br/meditacao-da-mulher-2/", "Meditação da Mulher"),
            ("https://mais.cpb.com.br/meditacao-jovem/", "Meditação Jovem")
        ]

        for url, title in meditation_sources:
            result = scrape_meditation(url, title)
            print(f"--- Processando: {title} ---\n{result}\n")

            if not result.startswith("Erro"):
                send_telegram_message(result, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
            else:
                print(f"A mensagem para '{title}' não foi enviada devido a um erro de scraping.")
