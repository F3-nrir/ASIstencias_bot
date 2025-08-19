import os
import logging
import requests
import time
from threading import Thread

logger = logging.getLogger(__name__)

class KeepAlive:
    def __init__(self):
        # Obtener la URL del servicio desde variables de entorno
        # Render.com proporciona automáticamente RENDER_EXTERNAL_URL
        self.service_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000')
        self.health_endpoint = f"{self.service_url}/health"
        self.interval = 600  # 10 minutos en segundos
        self.running = False
        
    def ping_service(self):
        """Hacer ping al servicio para mantenerlo activo"""
        try:
            response = requests.get(self.health_endpoint, timeout=30)
            if response.status_code == 200:
                logger.info("Keep-alive ping exitoso")
            else:
                logger.warning(f"Keep-alive ping falló con código: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en keep-alive ping: {e}")
        except Exception as e:
            logger.error(f"Error inesperado en keep-alive: {e}")
    
    def start_keep_alive(self):
        """Iniciar el sistema de keep-alive"""
        self.running = True
        logger.info(f"Iniciando keep-alive cada {self.interval} segundos")
        
        def keep_alive_loop():
            # Esperar 5 minutos antes del primer ping para que el servicio se inicie completamente
            time.sleep(300)
            
            while self.running:
                self.ping_service()
                time.sleep(self.interval)
        
        thread = Thread(target=keep_alive_loop, daemon=True)
        thread.start()
        logger.info("Keep-alive thread iniciado")
    
    def stop_keep_alive(self):
        """Detener el sistema de keep-alive"""
        self.running = False
        logger.info("Keep-alive detenido")
