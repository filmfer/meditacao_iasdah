import os
import requests

def send_telegram_alert():
    # Reuses your existing bot token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    # Uses your new personal chat ID secret
    personal_chat_id = os.getenv('TELEGRAM_PERSONAL_CHAT_ID')

    if not bot_token or not personal_chat_id:
        print("CRITICAL MONITORING ERROR: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_PERSONAL_CHAT_ID variables.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    alert_text = (
        "🚨 *FALHA CRÍTICA NO BOT* 🚨\n\n"
        "O script de meditações falhou ao autenticar no WhatsApp.\n"
        "A *sessão do WhatsApp expirou* ou foi desconectada.\n\n"
        "⚠️ *Ação necessária:* Vá aos logs do GitHub Actions para gerar e scanear um novo QR Code manualmente."
    )

    payload = {
        'chat_id': personal_chat_id,
        'text': alert_text,
        'parse_mode': 'Markdown'  # Renders the text with bold styling
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        print("Telegram personal failure alert sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Telegram alert: {e}")

if __name__ == "__main__":
    send_telegram_alert()
