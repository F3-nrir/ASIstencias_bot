import os
import logging
import asyncio
import pytz
import json
import time
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import requests

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Zona horaria de Cuba
CUBA_TZ = pytz.timezone('America/Havana')

# Almacenamiento temporal de configuraciones de usuario
user_configs = {}
user_states = {}

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

class OdooAPI:
    def __init__(self, url, db, username, password):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.session_id = None
    
    def authenticate(self):
        """Autenticar con Odoo usando requests"""
        try:
            auth_url = f"{self.url}/web/session/authenticate"
            auth_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "db": self.db,
                    "login": self.username,
                    "password": self.password
                },
                "id": 1
            }
            
            response = requests.post(auth_url, json=auth_data)
            result = response.json()
            
            if 'error' in result:
                logger.error(f"Error de autenticación: {result['error']}")
                return False
            
            if result.get('result') and result['result'].get('uid'):
                self.uid = result['result']['uid']
                self.session_id = result['result'].get('session_id')
                logger.info(f"Autenticación exitosa. UID: {self.uid}")
                return True
            else:
                logger.error("Credenciales inválidas")
                return False
                
        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return False
    
    def get_employee_id(self):
        """Obtener el ID del empleado asociado al usuario"""
        try:
            search_url = f"{self.url}/web/dataset/call_kw"
            search_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "hr.employee",
                    "method": "search_read",
                    "args": [[["user_id", "=", self.uid]]],
                    "kwargs": {
                        "fields": ["id", "name"],
                        "context": {"kiosk_mode": True}
                    }
                },
                "id": 1
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Cookie': f'session_id={self.session_id}' if self.session_id else ''
            }
            
            response = requests.post(search_url, json=search_data, headers=headers)
            result = response.json()
            
            if 'error' in result:
                logger.error(f"Error obteniendo empleado: {result['error']}")
                return None
            
            employees = result.get('result', [])
            if employees:
                return employees[0]['id']
            else:
                logger.error("No se encontró empleado asociado al usuario")
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo empleado: {e}")
            return None
    
    def create_attendance(self, employee_id):
        """Crear registro de asistencia (entrada)"""
        try:
            create_url = f"{self.url}/web/dataset/call_kw"
            create_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "hr.attendance",
                    "method": "create",
                    "args": [{
                        "employee_id": employee_id,
                        "check_in": datetime.now(CUBA_TZ).strftime('%Y-%m-%d %H:%M:%S')
                    }],
                    "kwargs": {
                        "context": {"kiosk_mode": True}
                    }
                },
                "id": 1
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Cookie': f'session_id={self.session_id}' if self.session_id else ''
            }
            
            response = requests.post(create_url, json=create_data, headers=headers)
            result = response.json()
            
            if 'error' in result:
                logger.error(f"Error creando asistencia: {result['error']}")
                return False
            
            logger.info(f"Asistencia creada exitosamente. ID: {result.get('result')}")
            return True
                
        except Exception as e:
            logger.error(f"Error creando asistencia: {e}")
            return False
    
    def close_attendance(self, employee_id):
        """Cerrar registro de asistencia abierto (salida)"""
        try:
            search_url = f"{self.url}/web/dataset/call_kw"
            search_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "hr.attendance",
                    "method": "search_read",
                    "args": [[
                        ["employee_id", "=", employee_id],
                        ["check_out", "=", False]
                    ]],
                    "kwargs": {
                        "fields": ["id"],
                        "limit": 1,
                        "context": {"kiosk_mode": True}
                    }
                },
                "id": 1
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Cookie': f'session_id={self.session_id}' if self.session_id else ''
            }
            
            response = requests.post(search_url, json=search_data, headers=headers)
            result = response.json()
            
            if 'error' in result:
                logger.error(f"Error buscando asistencia: {result['error']}")
                return False
            
            attendances = result.get('result', [])
            if not attendances:
                logger.warning("No hay asistencia abierta para cerrar")
                return False
            
            attendance_id = attendances[0]['id']
            update_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "hr.attendance",
                    "method": "write",
                    "args": [
                        [attendance_id],
                        {"check_out": datetime.now(CUBA_TZ).strftime('%Y-%m-%d %H:%M:%S')}
                    ],
                    "kwargs": {
                        "context": {"kiosk_mode": True}
                    }
                },
                "id": 1
            }
            
            response = requests.post(search_url, json=update_data, headers=headers)
            result = response.json()
            
            if 'error' in result:
                logger.error(f"Error cerrando asistencia: {result['error']}")
                return False
            
            logger.info(f"Asistencia cerrada exitosamente. ID: {attendance_id}")
            return True
                
        except Exception as e:
            logger.error(f"Error cerrando asistencia: {e}")
            return False
    
    def get_open_attendance(self, employee_id):
        """Obtener asistencia abierta del empleado"""
        try:
            search_url = f"{self.url}/web/dataset/call_kw"
            search_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "hr.attendance",
                    "method": "search_read",
                    "args": [[
                        ["employee_id", "=", employee_id],
                        ["check_out", "=", False]
                    ]],
                    "kwargs": {
                        "fields": ["id", "check_in"],
                        "limit": 1,
                        "context": {"kiosk_mode": True}
                    }
                },
                "id": 1
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Cookie': f'session_id={self.session_id}' if self.session_id else ''
            }
            
            response = requests.post(search_url, json=search_data, headers=headers)
            result = response.json()
            
            if 'error' in result:
                logger.error(f"Error buscando asistencia abierta: {result['error']}")
                return None
            
            attendances = result.get('result', [])
            if attendances:
                return attendances[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo asistencia abierta: {e}")
            return None

def handle_start(bot, chat_id, user_id):
    """Comando /start"""
    if user_id in user_configs:
        text = (
            "¡Hola! Ya tienes configurado tu bot de asistencias.\n\n"
            "Comandos disponibles:\n"
            "/config - Reconfigurar conexión a Odoo\n"
            "/status - Ver estado de configuración\n"
            "/test - Probar conexión\n"
            "/manual_in - Marcar entrada manual\n"
            "/manual_out - Marcar salida manual\n"
            "/check_status - Ver si tienes asistencia abierta"
        )
    else:
        text = (
            "¡Bienvenido al Bot de Asistencias Odoo! 🤖\n\n"
            "Para comenzar, necesito que configures tu conexión a Odoo.\n"
            "Usa el comando /config para empezar."
        )
    
    bot.send_message(chat_id, text)

def handle_config(bot, chat_id, user_id):
    """Iniciar configuración de Odoo"""
    user_states[user_id] = "waiting_url"
    text = (
        "🔧 Configuración de Odoo\n\n"
        "Por favor, envía la URL de tu servidor Odoo:\n"
        "Ejemplo: https://mi-odoo.com"
    )
    bot.send_message(chat_id, text)

def handle_status(bot, chat_id, user_id):
    """Ver estado de configuración"""
    if user_id not in user_configs:
        bot.send_message(chat_id, "❌ No tienes configuración guardada. Usa /config para configurar.")
        return
    
    config = user_configs[user_id]
    text = (
        f"✅ Configuración actual:\n\n"
        f"🌐 URL: {config['url']}\n"
        f"🗄️ Base de datos: {config['db']}\n"
        f"👤 Usuario: {config['username']}\n"
        f"🔑 Contraseña: {'*' * len(config['password'])}\n\n"
        f"⏰ Horarios programados:\n"
        f"📅 Lunes a Jueves: 8:00 AM - 5:30 PM\n"
        f"📅 Viernes: 8:00 AM - 4:30 PM"
    )
    bot.send_message(chat_id, text)

def handle_test(bot, chat_id, user_id):
    """Probar conexión con Odoo"""
    if user_id not in user_configs:
        bot.send_message(chat_id, "❌ No tienes configuración guardada. Usa /config para configurar.")
        return
    
    bot.send_message(chat_id, "🔄 Probando conexión con Odoo...")
    
    config = user_configs[user_id]
    odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
    
    if odoo.authenticate():
        employee_id = odoo.get_employee_id()
        if employee_id:
            text = f"✅ Conexión exitosa!\n👤 Empleado ID: {employee_id}"
        else:
            text = "⚠️ Conexión exitosa pero no se encontró empleado asociado."
    else:
        text = "❌ Error de conexión."
    
    bot.send_message(chat_id, text)

def handle_manual_in(bot, chat_id, user_id):
    """Marcar entrada manual"""
    if user_id not in user_configs:
        bot.send_message(chat_id, "❌ No tienes configuración guardada. Usa /config para configurar.")
        return
    
    bot.send_message(chat_id, "🔄 Marcando entrada...")
    
    config = user_configs[user_id]
    odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
    
    if odoo.authenticate():
        employee_id = odoo.get_employee_id()
        if employee_id and odoo.create_attendance(employee_id):
            now = datetime.now(CUBA_TZ)
            text = (
                f"✅ Entrada marcada exitosamente!\n"
                f"🕐 Hora: {now.strftime('%H:%M:%S')}\n"
                f"📅 Fecha: {now.strftime('%d/%m/%Y')}"
            )
        else:
            text = "❌ Error al marcar entrada."
    else:
        text = "❌ Error de conexión."
    
    bot.send_message(chat_id, text)

def handle_manual_out(bot, chat_id, user_id):
    """Marcar salida manual"""
    if user_id not in user_configs:
        bot.send_message(chat_id, "❌ No tienes configuración guardada. Usa /config para configurar.")
        return
    
    bot.send_message(chat_id, "🔄 Marcando salida...")
    
    config = user_configs[user_id]
    odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
    
    if odoo.authenticate():
        employee_id = odoo.get_employee_id()
        if employee_id and odoo.close_attendance(employee_id):
            now = datetime.now(CUBA_TZ)
            text = (
                f"✅ Salida marcada exitosamente!\n"
                f"🕐 Hora: {now.strftime('%H:%M:%S')}\n"
                f"📅 Fecha: {now.strftime('%d/%m/%Y')}"
            )
        else:
            text = "❌ Error al marcar salida o no hay entrada abierta."
    else:
        text = "❌ Error de conexión."
    
    bot.send_message(chat_id, text)

def handle_check_status(bot, chat_id, user_id):
    """Verificar si hay asistencia abierta y desde qué hora"""
    if user_id not in user_configs:
        bot.send_message(chat_id, "❌ No tienes configuración guardada. Usa /config para configurar.")
        return
    
    bot.send_message(chat_id, "🔄 Verificando estado de asistencia...")
    
    config = user_configs[user_id]
    odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
    
    if odoo.authenticate():
        employee_id = odoo.get_employee_id()
        if employee_id:
            open_attendance = odoo.get_open_attendance(employee_id)
            if open_attendance:
                check_in_str = open_attendance['check_in']
                check_in_utc = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')
                check_in_utc = pytz.utc.localize(check_in_utc)
                check_in_cuba = check_in_utc.astimezone(CUBA_TZ)
                
                text = (
                    f"✅ Tienes una asistencia abierta\n\n"
                    f"🕐 Hora de entrada: {check_in_cuba.strftime('%H:%M:%S')}\n"
                    f"📅 Fecha: {check_in_cuba.strftime('%d/%m/%Y')}\n"
                    f"⏱️ Tiempo trabajado: {datetime.now(CUBA_TZ) - check_in_cuba}"
                )
            else:
                text = (
                    "❌ No tienes ninguna asistencia abierta\n\n"
                    "Puedes marcar entrada con /manual_in"
                )
        else:
            text = "❌ No se encontró empleado asociado."
    else:
        text = "❌ Error de conexión."
    
    bot.send_message(chat_id, text)

def handle_message(bot, chat_id, user_id, text):
    """Manejar mensajes durante la configuración"""
    if user_id not in user_states:
        bot.send_message(chat_id, "Usa /start para comenzar o /config para configurar.")
        return
    
    state = user_states[user_id]
    
    if state == "waiting_url":
        if not text.startswith(('http://', 'https://')):
            bot.send_message(chat_id, "❌ Por favor, ingresa una URL válida que comience con http:// o https://")
            return
        
        if user_id not in user_configs:
            user_configs[user_id] = {}
        user_configs[user_id]['url'] = text.rstrip('/')
        user_states[user_id] = "waiting_db"
        
        bot.send_message(chat_id, "✅ URL guardada.\n\nAhora envía el nombre de tu base de datos:")
    
    elif state == "waiting_db":
        user_configs[user_id]['db'] = text
        user_states[user_id] = "waiting_username"
        
        bot.send_message(chat_id, "✅ Base de datos guardada.\n\nAhora envía tu nombre de usuario de Odoo:")
    
    elif state == "waiting_username":
        user_configs[user_id]['username'] = text
        user_states[user_id] = "waiting_password"
        
        bot.send_message(chat_id, "✅ Usuario guardado.\n\nPor último, envía tu contraseña de Odoo:")
    
    elif state == "waiting_password":
        user_configs[user_id]['password'] = text
        del user_states[user_id]
        
        bot.send_message(chat_id, "✅ ¡Configuración completada!\n\nProbando conexión...")
        
        config = user_configs[user_id]
        odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
        
        if odoo.authenticate():
            employee_id = odoo.get_employee_id()
            if employee_id:
                text = (
                    "🎉 ¡Todo configurado correctamente!\n\n"
                    "El bot marcará automáticamente:\n"
                    "📅 Lunes a Jueves: 8:00 AM - 5:30 PM\n"
                    "📅 Viernes: 8:00 AM - 4:30 PM\n\n"
                    "También puedes usar los comandos manuales:\n"
                    "/manual_in - Marcar entrada\n"
                    "/manual_out - Marcar salida\n"
                    "/status - Ver configuración\n"
                    "/test - Probar conexión"
                )
            else:
                text = (
                    "⚠️ Conexión exitosa pero no se encontró un empleado asociado a tu usuario.\n"
                    "Verifica que tu usuario de Odoo esté vinculado a un empleado."
                )
        else:
            text = "❌ Error de conexión. Verifica tus credenciales y usa /config para reconfigurar."
            del user_configs[user_id]
        
        bot.send_message(chat_id, text)

def scheduled_check_in():
    """Tarea programada para marcar entrada (8:00 AM)"""
    logger.info("Ejecutando marcado automático de entrada...")
    
    for user_id, config in user_configs.items():
        try:
            odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
            
            if odoo.authenticate():
                employee_id = odoo.get_employee_id()
                if employee_id:
                    if odoo.create_attendance(employee_id):
                        logger.info(f"Entrada marcada para usuario {user_id}")
                    else:
                        logger.error(f"Error marcando entrada para usuario {user_id}")
                else:
                    logger.error(f"No se encontró empleado para usuario {user_id}")
            else:
                logger.error(f"Error de autenticación para usuario {user_id}")
                
        except Exception as e:
            logger.error(f"Error en entrada automática para usuario {user_id}: {e}")

def scheduled_check_out():
    """Tarea programada para marcar salida"""
    logger.info("Ejecutando marcado automático de salida...")
    
    for user_id, config in user_configs.items():
        try:
            odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
            
            if odoo.authenticate():
                employee_id = odoo.get_employee_id()
                if employee_id:
                    if odoo.close_attendance(employee_id):
                        logger.info(f"Salida marcada para usuario {user_id}")
                    else:
                        logger.error(f"Error marcando salida para usuario {user_id}")
                else:
                    logger.error(f"No se encontró empleado para usuario {user_id}")
            else:
                logger.error(f"Error de autenticación para usuario {user_id}")
                
        except Exception as e:
            logger.error(f"Error en salida automática para usuario {user_id}: {e}")

def main():
    """Función principal"""
    bot = TelegramBot(BOT_TOKEN)
    
    # Configurar scheduler
    scheduler = AsyncIOScheduler(timezone=CUBA_TZ)
    
    # Entrada a las 8:00 AM, lunes a viernes
    scheduler.add_job(
        scheduled_check_in,
        CronTrigger(hour=8, minute=0, day_of_week='mon-fri'),
        id='check_in'
    )
    
    # Salida a las 5:30 PM, lunes a jueves
    scheduler.add_job(
        scheduled_check_out,
        CronTrigger(hour=17, minute=30, day_of_week='mon-thu'),
        id='check_out_weekdays'
    )
    
    # Salida a las 4:30 PM, viernes
    scheduler.add_job(
        scheduled_check_out,
        CronTrigger(hour=16, minute=30, day_of_week='fri'),
        id='check_out_friday'
    )
    
    scheduler.start()
    logger.info("Scheduler iniciado")
    
    logger.info("Bot iniciado")
    
    while True:
        try:
            updates = bot.get_updates()
            
            if updates and updates.get('ok'):
                for update in updates.get('result', []):
                    bot.offset = update['update_id'] + 1
                    
                    if 'message' in update:
                        message = update['message']
                        chat_id = message['chat']['id']
                        user_id = message['from']['id']
                        
                        if 'text' in message:
                            text = message['text']
                            
                            # Manejar comandos
                            if text == '/start':
                                handle_start(bot, chat_id, user_id)
                            elif text == '/config':
                                handle_config(bot, chat_id, user_id)
                            elif text == '/status':
                                handle_status(bot, chat_id, user_id)
                            elif text == '/test':
                                handle_test(bot, chat_id, user_id)
                            elif text == '/manual_in':
                                handle_manual_in(bot, chat_id, user_id)
                            elif text == '/manual_out':
                                handle_manual_out(bot, chat_id, user_id)
                            elif text == '/check_status':
                                handle_check_status(bot, chat_id, user_id)
                            elif not text.startswith('/'):
                                handle_message(bot, chat_id, user_id, text)
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error en loop principal: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()

