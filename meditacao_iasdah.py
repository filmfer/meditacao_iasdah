import requests
import os
import smtplib
import ssl
from email.message import EmailMessage
import time
from bs4 import BeautifulSoup
import datetime
import warnings
from urllib3.exceptions import InsecureRequestWarning

# --- CONFIGURAÇÕES ---
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 15
EMAIL_RECEIVER = "filmfer@gmail.com"

# Suprime avisos de SSL explicitamente
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

def format_date_in_portuguese(date_obj):
    """
    Formata a data em português, independente do sistema operativo.
    """
    dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    
    weekday = dias[date_obj.weekday()]
    day = date_obj.day
    month = meses[date_obj.month - 1]
    
    return f"{weekday}, {day} de {month}"

def send_error_email(subject, body):
    """Envia um email de notificação de erro."""
    email_sender = os.getenv('EMAIL_ADDRESS')
    email_password = os.getenv('GMAIL_APP_PASSWORD')

    if not email_sender or not email_password:
        print("ERRO CRÍTICO: Variáveis de ambiente para envio de email (EMAIL_ADDRESS, GMAIL_APP_PASSWORD) não definidas. Não é possível notificar.")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = email_sender
    msg['To'] = EMAIL_RECEIVER

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(email_sender, email_password)
            server.send_message(msg)
            print(f"Email de notificação de erro enviado com sucesso para {EMAIL_RECEIVER}.")
    except Exception as e:
        print(f"Falha catastrófica ao enviar o email de notificação: {e}")

# --- NEW FUNCTION ---
# This helper function is necessary to use Markdown safely.
def escape_markdown(text: str) -> str:
    """Escapa caracteres especiais para o modo MarkdownV2 do Telegram."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return "".join(f'\\{char}' if char in escape_chars else char for char in text)

# --- FUNÇÃO DE LIMPEZA ADICIONADA ---
def clean_scraped_text(text: str) -> str:
    """
    Remove sequências de caracteres indesejadas do texto extraído.
    Remove as sequências " /" e " \".
    """
    text = text.replace(" /", "")
    text = text.replace(" \\", "")
    return text

def scrape_meditation(base_url, meditacao_matinal_title):
    """Faz o scraping da página da meditação e retorna o texto formatado."""
    try:
        response = requests.get(base_url, verify=False, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        link_tag = soup.find("a", class_="mdl-button mdl-button--colored mdl-js-button mdl-js-ripple-effect")
        if not link_tag or not link_tag.has_attr("href"):
            return None, "Link da meditação diária não encontrado"

        meditation_url = link_tag["href"]
        response = requests.get(meditation_url, verify=False, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        today = datetime.date.today()

        # --- MODIFIED ---: Re-added Markdown formatting (* for bold, _ for italic)
        # All scraped text is now escaped before formatting is applied.
        meditacao_matinal = f"**{escape_markdown(meditacao_matinal_title)}**"
        weekday_date = escape_markdown(format_date_in_portuguese(today))

        title_tag = soup.find("div", class_="mdl-typography--headline")
        title = title_tag.text.strip() if title_tag else "Título não encontrado"
        title = clean_scraped_text(title)
        title_text = f"**{escape_markdown(title)}**"

        reference_text_tag = soup.find("div", class_="descriptionText versoBiblico")
        reference_text = reference_text_tag.text.strip() if reference_text_tag else "Verso não encontrado"
        reference_text = clean_scraped_text(reference_text)
        reference_text_content = f"__{escape_markdown(reference_text)}__"

        meditation_content_tag = soup.find("div", class_="conteudoMeditacao")
        meditation_content = meditation_content_tag.text.strip() if meditation_content_tag else "Conteúdo não encontrado"
        meditation_content = clean_scraped_text(meditation_content)
        meditation_content = escape_markdown(meditation_content)

        youtube_iframe_tag = soup.find("iframe", {"src": lambda src: src and "youtube.com/embed" in src})
        youtube_link = youtube_iframe_tag["src"].split('?')[0].replace("embed/", "watch?v=") if youtube_iframe_tag else ""
        
        escaped_youtube_link = escape_markdown(youtube_link)
        escaped_meditation_url = escape_markdown(meditation_url)

        formatted_text = (
            f"{meditacao_matinal}\n"
            f"{weekday_date}\n\n"
            f"{title_text}\n"
            f"{reference_text_content}\n\n"
            f"{meditation_content}\n\n"
            f"{escaped_youtube_link}\n\n"
            f"{escaped_meditation_url}\n\n"
        )
        return formatted_text.strip(), None

    except requests.exceptions.RequestException as e:
        return None, f"Erro de Request (Scraping): {e}"
    except Exception as e:
        return None, f"Erro inesperado (Scraping): {e}"

def send_telegram_message(text, bot_token, chat_id):
    """Envia uma mensagem para o Telegram e retorna um status de sucesso/falha."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        # --- MODIFIED ---: Re-enabled MarkdownV2 to render the formatting.
        'parse_mode': 'MarkdownV2'
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        print(f"Mensagem enviada com sucesso para o Telegram (Chat ID: {chat_id})")
        return True, None
    except requests.exceptions.RequestException as e:
        error_details = f"Erro de Request (Telegram): {e}"
        if 'response' in locals() and hasattr(response, 'text') and response.text:
            error_details += f"\nResposta da API: {response.text}"
        return False, error_details

if __name__ == "__main__":
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERRO CRÍTICO: As variáveis de ambiente do Telegram não foram definidas.")
        send_error_email(
            "Falha Crítica no Bot de Meditações",
            "O bot não pôde ser executado porque as variáveis de ambiente TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não foram encontradas."
        )
    else:
        meditation_sources = [
            ("https://mais.cpb.com.br/meditacoes-diarias/", "Meditação Matinal"),
            ("https://mais.cpb.com.br/meditacao-da-mulher-2/", "Meditação da Mulher"),
            ("https://mais.cpb.com.br/meditacao-jovem/", "Meditação Jovem")
        ]

        for url, title in meditation_sources:
            print(f"--- Processando: {title} ---")
            
            scraped_content = None
            last_scrape_error = ""
            for attempt in range(1, MAX_RETRIES + 1):
                print(f"Tentativa de scraping nº {attempt}/{MAX_RETRIES} para '{title}'...")
                content, error = scrape_meditation(url, title)
                if content:
                    scraped_content = content
                    print("Scraping bem-sucedido.")
                    break
                last_scrape_error = error
                print(f"Falha no scraping: {error}. A aguardar {RETRY_DELAY_SECONDS}s para tentar de novo.")
                time.sleep(RETRY_DELAY_SECONDS)
            
            if not scraped_content:
                print(f"ERRO FINAL: Scraping para '{title}' falhou após {MAX_RETRIES} tentativas.")
                send_error_email(
                    f"Falha no Scraping da Meditação: {title}",
                    f"O bot não conseguiu extrair o conteúdo para a meditação '{title}'.\n\nÚltimo erro registado:\n{last_scrape_error}"
                )
                continue

            send_success = False
            last_send_error = ""
            for attempt in range(1, MAX_RETRIES + 1):
                print(f"Tentativa de envio para o Telegram nº {attempt}/{MAX_RETRIES} para '{title}'...")
                success, error = send_telegram_message(scraped_content, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
                if success:
                    send_success = True
                    break
                last_send_error = error
                print(f"Falha no envio: {error}. A aguardar {RETRY_DELAY_SECONDS}s para tentar de novo.")
                time.sleep(RETRY_DELAY_SECONDS)

            if not send_success:
                print(f"ERRO FINAL: Envio para o Telegram para '{title}' falhou após {MAX_RETRIES} tentativas.")
                send_error_email(
                    f"Falha no Envio para o Telegram: {title}",
                    f"O bot não conseguiu enviar a meditação '{title}' para o Telegram.\n\nÚltimo erro registado:\n{last_send_error}"
                )

        print("\n--- Processo concluído. ---")
