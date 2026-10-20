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
from urllib.parse import urljoin

# --- CONFIGURAÇÕES ---
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 20
EMAIL_RECEIVER = "filmfer@gmail.com"
# O ficheiro whatsapp_msg.txt é limpo apenas quando todas as 3 meditações
# são processadas com sucesso (no final do script), para evitar perder
# conteúdo de execuções anteriores em caso de falha parcial.

# Suprime avisos de SSL explícitamente
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

def format_date_in_portuguese(date_obj):
    """Formata a data em português."""
    dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    
    weekday = dias[date_obj.weekday()]
    day = date_obj.day
    month = meses[date_obj.month - 1]
    
    return f"{weekday}, {day} de {month}"

def send_error_email(subject, body):
    """Envia um email de notificação de erro interno de processamento/scraping."""
    email_sender = os.getenv('EMAIL_ADDRESS')
    email_password = os.getenv('GMAIL_APP_PASSWORD')

    if not email_sender or not email_password:
        print("ERRO CRÍTICO: Variáveis de ambiente para envio de email não definidas.")
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

def escape_markdown(text: str) -> str:
    """Escapa caracteres especiais apenas para o modo MarkdownV2 do Telegram."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return "".join(f'\\{char}' if char in escape_chars else char for char in text)

def clean_scraped_text(text: str) -> str:
    """Remove sequências de caracteres indesejadas do texto extraído."""
    text = text.replace(" /", "")
    text = text.replace(" \\", "")
    return text

# Seletores alternativos para o link da meditação (em caso de mudança no website)
LINK_SELECTORS = [
    "a.mdl-button.mdl-button--colored.mdl-js-button.mdl-js-ripple-effect",
    "a.mdl-button--colored",
    "a[href*='post_type=meditacao']",
]

# Marcadores que indicam que a extração falhou (placeholders)
PLACEHOLDER_TEXTOS = [
    "título não encontrado",
    "verso não encontrado",
    "conteúdo não encontrado",
]


def _encontrar_link_meditacao(soup, base_url):
    """Tenta múltiplos seletores para encontrar o link da meditação diária."""
    for selector in LINK_SELECTORS:
        tag = soup.select_one(selector)
        if tag and tag.has_attr("href"):
            href = tag["href"]
            # Garantir URL absoluta
            if href.startswith("http"):
                return href
            return urljoin(base_url, href)
    return None


def _conteudo_valido(texto, campo_nome):
    """Verifica se o texto extraído não é vazio nem um placeholder de falha."""
    if not texto or not texto.strip():
        print(f"  [AVISO] {campo_nome} está vazio.")
        return False
    texto_lower = texto.strip().lower()
    for ph in PLACEHOLDER_TEXTOS:
        if ph in texto_lower:
            print(f"  [AVISO] {campo_nome} parece ser um placeholder de falha: '{texto.strip()[:60]}...'")
            return False
    return True


def scrape_meditation(base_url, meditacao_matinal_title):
    """Faz o scraping e retorna DUAS versões do texto formatado (Telegram e
    WhatsApp) mais o URL de pré-visualização (thumbnail) para o Telegram."""
    try:
        response = requests.get(base_url, verify=False, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        meditation_url = _encontrar_link_meditacao(soup, base_url)
        if not meditation_url:
            return None, None, None, "Link da meditação diária não encontrado (nenhum seletor bateu)"

        print(f"  [INFO] URL da meditação: {meditation_url}")

        response = requests.get(meditation_url, verify=False, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        today = datetime.date.today()
        weekday_date = format_date_in_portuguese(today)

        title_tag = soup.find("div", class_="mdl-typography--headline")
        title = clean_scraped_text(title_tag.text.strip() if title_tag else "")
        if not _conteudo_valido(title, "Título"):
            return None, None, None, "Título da meditação não encontrado ou inválido"

        reference_text_tag = soup.find("div", class_="descriptionText versoBiblico")
        reference_text = clean_scraped_text(reference_text_tag.text.strip() if reference_text_tag else "")
        if not _conteudo_valido(reference_text, "Verso bíblico"):
            return None, None, None, "Verso bíblico não encontrado ou inválido"

        meditation_content_tag = soup.find("div", class_="conteudoMeditacao")
        meditation_content = clean_scraped_text(meditation_content_tag.text.strip() if meditation_content_tag else "")
        if not _conteudo_valido(meditation_content, "Conteúdo da meditação"):
            return None, None, None, "Conteúdo da meditação não encontrado ou inválido"

        youtube_iframe_tag = soup.find("iframe", {"src": lambda src: src and "youtube.com/embed" in src})
        youtube_link = youtube_iframe_tag["src"].split('?')[0].replace("embed/", "watch?v=") if youtube_iframe_tag else ""

        print(f"  [OK] Título extraído: {title[:80]}...")
        print(f"  [OK] Conteúdo: {len(meditation_content)} caracteres")
        print(f"  [OK] YouTube: {youtube_link if youtube_link else 'sem vídeo'}")

        # --- VERSÃO TELEGRAM (Com escapes pesados MarkdownV2) ---
        telegram_text = (
            f"*{escape_markdown(meditacao_matinal_title)}*\n"
            f"{escape_markdown(weekday_date)}\n\n"
            f"*{escape_markdown(title)}*\n"
            f"_{escape_markdown(reference_text)}_\n\n"
            f"{escape_markdown(meditation_content)}\n\n"
            f"{escape_markdown(youtube_link)}\n\n"
            f"{escape_markdown(meditation_url)}\n\n"
        )

        # --- VERSÃO WHATSAPP (Apenas * e _, sem escapes e contra-barras) ---
        whatsapp_text = (
            f"*{meditacao_matinal_title}*\n"
            f"{weekday_date}\n\n"
            f"*{title}*\n"
            f"_{reference_text}_\n\n"
            f"{meditation_content}\n\n"
            f"{youtube_link}\n\n"
            f"{meditation_url}\n\n"
        )

        # URL para forçar a pré-visualização (thumbnail) no Telegram: o do
        # vídeo do YouTube, se existir; caso contrário, o da própria meditação.
        preview_url = youtube_link if youtube_link else meditation_url

        return telegram_text.strip(), whatsapp_text.strip(), preview_url, None

    except requests.exceptions.RequestException as e:
        return None, None, None, f"Erro de Request (Scraping): {e}"
    except Exception as e:
        return None, None, None, f"Erro inesperado (Scraping): {e}"

def send_telegram_message(text, bot_token, chat_id, preview_url=None):
    """Envia uma mensagem para o canal/grupo do Telegram.

    Se preview_url for fornecido, força a pré-visualização (thumbnail) desse
    URL no topo da mensagem via link_preview_options (Bot API 7.0+) — garante
    a miniatura mesmo que o URL no texto vá escapado para MarkdownV2.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'MarkdownV2'
    }
    if preview_url:
        payload['link_preview_options'] = {
            'url': preview_url,
            'show_above_text': True
        }
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        print(f"Mensagem enviada com sucesso para o Telegram (Chat ID: {chat_id})")
        return True, None
    except requests.exceptions.RequestException as e:
        error_details = f"Erro de Request (Telegram): {e}"
        if e.response is not None and hasattr(e.response, 'text'):
            error_details += f"\nResposta da API: {e.response.text}"
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

        resultados = []

        for url, title in meditation_sources:
            print("\n" + "="*60)
            print("--- Processando: " + title + " ---")
            print("="*60)

            telegram_content = None
            whatsapp_content = None
            telegram_preview_url = None
            last_scrape_error = ""
            scraping_ok = False
            telegram_ok = False
            whatsapp_ok = False

            for attempt in range(1, MAX_RETRIES + 1):
                print("Tentativa de scraping nº " + str(attempt) + "/" + str(MAX_RETRIES) + " para '" + title + "'...")
                t_content, w_content, t_preview, error = scrape_meditation(url, title)
                if t_content and w_content:
                    telegram_content = t_content
                    whatsapp_content = w_content
                    telegram_preview_url = t_preview
                    scraping_ok = True
                    print("Scraping bem-sucedido.")
                    break
                last_scrape_error = error
                print("Falha no scraping: " + error + ". A aguardar " + str(RETRY_DELAY_SECONDS) + "s para tentar de novo.")
                time.sleep(RETRY_DELAY_SECONDS)

            if not scraping_ok:
                print("ERRO FINAL: Scraping para '" + title + "' falhou após " + str(MAX_RETRIES) + " tentativas.")
                send_error_email(
                    "Falha no Scraping da Meditação: " + title,
                    "O bot não conseguiu extrair o conteúdo para a meditação '" + title + "'.\n\nÚltimo erro registado:\n" + last_scrape_error
                )
                resultados.append((title, False, False, False))
                continue

            # --- ENVIO TELEGRAM ---
            last_send_error = ""
            for attempt in range(1, MAX_RETRIES + 1):
                print("Tentativa de envio para o Telegram nº " + str(attempt) + "/" + str(MAX_RETRIES) + " para '" + title + "'...")
                success, error = send_telegram_message(telegram_content, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, telegram_preview_url)
                if success:
                    telegram_ok = True
                    break
                last_send_error = error
                print("Falha no envio Telegram: " + error + ". A aguardar " + str(RETRY_DELAY_SECONDS) + "s para tentar de novo.")
                time.sleep(RETRY_DELAY_SECONDS)

            if not telegram_ok:
                print("ERRO FINAL: Envio para o Telegram para '" + title + "' falhou.")
                send_error_email(
                    "Falha no Envio para o Telegram: " + title,
                    "O bot não conseguiu enviar a meditação '" + title + "' para o Telegram.\n\nÚltimo erro registado:\n" + last_send_error
                )

            # --- SALVAR PAYLOAD DO WHATSAPP ---
            whatsapp_ok = True
            with open("whatsapp_msg.txt", "a", encoding="utf-8") as f:
                f.write(whatsapp_content + "\n\n===DIVISAO_MEDITACAO===\n\n")

            print("Meditação '" + title + "' segmentada e preparada para o WhatsApp com sucesso.")
            resultados.append((title, scraping_ok, telegram_ok, whatsapp_ok))

        # --- RESUMO FINAL ---
        print("\n" + "="*60)
        print("RESUMO FINAL DAS 3 MEDITAÇÕES")
        print("="*60)
        todas_ok = True
        for titulo, scrap_ok, tel_ok, wha_ok in resultados:
            status_scrap = "OK" if scrap_ok else "FALHA"
            status_tel = "OK" if tel_ok else "FALHA"
            status_wha = "OK" if wha_ok else "FALHA"
            print("  " + titulo + ": scraping=[" + status_scrap + "] telegram=[" + status_tel + "] whatsapp=[" + status_wha + "]")
            if not (scrap_ok and tel_ok and wha_ok):
                todas_ok = False

        if todas_ok:
            print("\n✅ Todas as 3 meditações foram processadas com sucesso.")
            if os.path.exists("whatsapp_msg.txt"):
                os.remove("whatsapp_msg.txt")
            open("whatsapp_msg.txt", "w", encoding="utf-8").close()
        else:
            print("\n⚠️  Alguma(s) meditação(ões) falhou(ram). O ficheiro whatsapp_msg.txt foi mantido para inspeção.")
            linhas_email = ["Nem todas as 3 meditações foram processadas com sucesso.\n\nResultados:"]
            for t, s, tg, w in resultados:
                linhas_email.append("  " + t + ": scraping=[" + ("OK" if s else "FALHA") + "] telegram=[" + ("OK" if tg else "FALHA") + "] whatsapp=[" + ("OK" if w else "FALHA") + "]")
            send_error_email(
                "Falha parcial no processamento das meditações",
                "\n".join(linhas_email)
            )
