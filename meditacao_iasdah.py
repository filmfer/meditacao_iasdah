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
        weekday_date = format_date_in_portuguese(today)

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
            f"{youtube_link}\n\n"
            f"{base_url}"
        )

        return formatted_text.strip()

    except requests.exceptions.RequestException as e:
        return f"Erro de Request para {base_url}: {e}"
    except Exception as e:
        return f"Erro inesperado para {base_url}: {e}"

def send_whatsapp_message(text, access_token, phone_number_id, to_number):
    """
    Envia uma mensagem de texto para um chat do WhatsApp (pode ser um grupo ou um número individual).
    """
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,  # This can be a phone number or a group ID
        "type": "text",
        "text": {
            "body": text  # WhatsApp supports a subset of Markdown (e.g., *bold*, _italic_)
        },
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Mensagem enviada com sucesso para o WhatsApp (Destino: {to_number})")
        # You might want to print the response data for debugging
        # print(f"API Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Falha ao enviar mensagem para o WhatsApp: {e}")
        if response is not None:
            print(f"Resposta da API: {response.text}")
    except Exception as e:
        print(f"Erro inesperado ao enviar mensagem para o WhatsApp: {e}")

if __name__ == "__main__":
    # Carrega as credenciais do WhatsApp a partir de variáveis de ambiente
    WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
    WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    WHATSAPP_GROUP_ID = os.getenv('WHATSAPP_GROUP_ID') # Or WHATSAPP_RECIPIENT_NUMBER for individual chats

    if not all([WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_GROUP_ID]):
        print("As variáveis de ambiente WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID e WHATSAPP_GROUP_ID não foram definidas.")
        print("Por favor, configure-as antes de executar o script.")
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
                # Send to WhatsApp
                send_whatsapp_message(result, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_GROUP_ID)
            else:
                print(f"A mensagem para '{title}' não foi enviada devido a um erro de scraping.")
