import json
import logging
import requests

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
    
    def send_message(self, chat_id, text, reply_markup=None):
        """Enviar mensaje usando requests"""
        url = f"{self.api_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        try:
            response = requests.post(url, data=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")
            return None
    
    def get_updates(self):
        """Obtener actualizaciones usando requests"""
        url = f"{self.api_url}/getUpdates"
        params = {
            'offset': self.offset,
            'timeout': 30
        }
        
        try:
            response = requests.get(url, params=params)
            return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo actualizaciones: {e}")
            return None
