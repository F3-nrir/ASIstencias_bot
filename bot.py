import os
import logging
import asyncio
import pytz
from datetime import datetime, time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import aiohttp
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8402582437:AAE0FFIRVBli09VCm5TpqTtbBvwVeOkqKmE')

# Zona horaria de Cuba
CUBA_TZ = pytz.timezone('America/Havana')

# Almacenamiento temporal de configuraciones de usuario (en producción usar base de datos)
user_configs = {}
user_states = {}

class OdooAPI:
    def __init__(self, url, db, username, password):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.session_id = None
    
    async def authenticate(self):
        """Autenticar con Odoo y obtener UID"""
        try:
            async with aiohttp.ClientSession() as session:
                # Endpoint de autenticación
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
                
                async with session.post(auth_url, json=auth_data) as response:
                    result = await response.json()
                    
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
    
    async def get_employee_id(self):
        """Obtener el ID del empleado asociado al usuario"""
        try:
            async with aiohttp.ClientSession() as session:
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
                
                async with session.post(search_url, json=search_data, headers=headers) as response:
                    result = await response.json()
                    
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
    
    async def create_attendance(self, employee_id):
        """Crear registro de asistencia (entrada)"""
        try:
            async with aiohttp.ClientSession() as session:
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
                
                async with session.post(create_url, json=create_data, headers=headers) as response:
                    result = await response.json()
                    
                    if 'error' in result:
                        logger.error(f"Error creando asistencia: {result['error']}")
                        return False
                    
                    logger.info(f"Asistencia creada exitosamente. ID: {result.get('result')}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error creando asistencia: {e}")
            return False
    
    async def close_attendance(self, employee_id):
        """Cerrar registro de asistencia abierto (salida)"""
        try:
            async with aiohttp.ClientSession() as session:
                # Buscar asistencia abierta
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
                
                async with session.post(search_url, json=search_data, headers=headers) as response:
                    result = await response.json()
                    
                    if 'error' in result:
                        logger.error(f"Error buscando asistencia: {result['error']}")
                        return False
                    
                    attendances = result.get('result', [])
                    if not attendances:
                        logger.warning("No hay asistencia abierta para cerrar")
                        return False
                    
                    # Cerrar la asistencia
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
                    
                    async with session.post(search_url, json=update_data, headers=headers) as response:
                        result = await response.json()
                        
                        if 'error' in result:
                            logger.error(f"Error cerrando asistencia: {result['error']}")
                            return False
                        
                        logger.info(f"Asistencia cerrada exitosamente. ID: {attendance_id}")
                        return True
                        
        except Exception as e:
            logger.error(f"Error cerrando asistencia: {e}")
            return False
    
    async def get_open_attendance(self, employee_id):
        """Obtener asistencia abierta del empleado"""
        try:
            async with aiohttp.ClientSession() as session:
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
                
                async with session.post(search_url, json=search_data, headers=headers) as response:
                    result = await response.json()
                    
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user_id = update.effective_user.id
    
    if user_id in user_configs:
        await update.message.reply_text(
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
        await update.message.reply_text(
            "¡Bienvenido al Bot de Asistencias Odoo! 🤖\n\n"
            "Para comenzar, necesito que configures tu conexión a Odoo.\n"
            "Usa el comando /config para empezar."
        )

async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Iniciar configuración de Odoo"""
    user_id = update.effective_user.id
    user_states[user_id] = "waiting_url"
    
    await update.message.reply_text(
        "🔧 Configuración de Odoo\n\n"
        "Por favor, envía la URL de tu servidor Odoo:\n"
        "Ejemplo: https://mi-odoo.com"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver estado de configuración"""
    user_id = update.effective_user.id
    
    if user_id not in user_configs:
        await update.message.reply_text("❌ No tienes configuración guardada. Usa /config para configurar.")
        return
    
    config = user_configs[user_id]
    await update.message.reply_text(
        f"✅ Configuración actual:\n\n"
        f"🌐 URL: {config['url']}\n"
        f"🗄️ Base de datos: {config['db']}\n"
        f"👤 Usuario: {config['username']}\n"
        f"🔑 Contraseña: {'*' * len(config['password'])}\n\n"
        f"⏰ Horarios programados:\n"
        f"📅 Lunes a Jueves: 8:00 AM - 5:30 PM\n"
        f"📅 Viernes: 8:00 AM - 4:30 PM"
    )

async def test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Probar conexión con Odoo"""
    user_id = update.effective_user.id
    
    if user_id not in user_configs:
        await update.message.reply_text("❌ No tienes configuración guardada. Usa /config para configurar.")
        return
    
    await update.message.reply_text("🔄 Probando conexión con Odoo...")
    
    config = user_configs[user_id]
    odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
    
    if await odoo.authenticate():
        employee_id = await odoo.get_employee_id()
        if employee_id:
            await update.message.reply_text(
                f"✅ Conexión exitosa!\n"
                f"👤 Empleado ID: {employee_id}"
            )
        else:
            await update.message.reply_text("⚠️ Conexión exitosa pero no se encontró empleado asociado.")
    else:
        await update.message.reply_text("❌ Error de conexión.")

async def manual_in(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Marcar entrada manual"""
    user_id = update.effective_user.id
    
    if user_id not in user_configs:
        await update.message.reply_text("❌ No tienes configuración guardada. Usa /config para configurar.")
        return
    
    await update.message.reply_text("🔄 Marcando entrada...")
    
    config = user_configs[user_id]
    odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
    
    if await odoo.authenticate():
        employee_id = await odoo.get_employee_id()
        if employee_id and await odoo.create_attendance(employee_id):
            now = datetime.now(CUBA_TZ)
            await update.message.reply_text(
                f"✅ Entrada marcada exitosamente!\n"
                f"🕐 Hora: {now.strftime('%H:%M:%S')}\n"
                f"📅 Fecha: {now.strftime('%d/%m/%Y')}"
            )
        else:
            await update.message.reply_text("❌ Error al marcar entrada.")
    else:
        await update.message.reply_text("❌ Error de conexión.")

async def manual_out(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Marcar salida manual"""
    user_id = update.effective_user.id
    
    if user_id not in user_configs:
        await update.message.reply_text("❌ No tienes configuración guardada. Usa /config para configurar.")
        return
    
    await update.message.reply_text("🔄 Marcando salida...")
    
    config = user_configs[user_id]
    odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
    
    if await odoo.authenticate():
        employee_id = await odoo.get_employee_id()
        if employee_id and await odoo.close_attendance(employee_id):
            now = datetime.now(CUBA_TZ)
            await update.message.reply_text(
                f"✅ Salida marcada exitosamente!\n"
                f"🕐 Hora: {now.strftime('%H:%M:%S')}\n"
                f"📅 Fecha: {now.strftime('%d/%m/%Y')}"
            )
        else:
            await update.message.reply_text("❌ Error al marcar salida o no hay entrada abierta.")
    else:
        await update.message.reply_text("❌ Error de conexión.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes durante la configuración"""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await update.message.reply_text("Usa /start para comenzar o /config para configurar.")
        return
    
    state = user_states[user_id]
    text = update.message.text
    
    if state == "waiting_url":
        if not text.startswith(('http://', 'https://')):
            await update.message.reply_text("❌ Por favor, ingresa una URL válida que comience con http:// o https://")
            return
        
        if user_id not in user_configs:
            user_configs[user_id] = {}
        user_configs[user_id]['url'] = text.rstrip('/')
        user_states[user_id] = "waiting_db"
        
        await update.message.reply_text(
            "✅ URL guardada.\n\n"
            "Ahora envía el nombre de tu base de datos:"
        )
    
    elif state == "waiting_db":
        user_configs[user_id]['db'] = text
        user_states[user_id] = "waiting_username"
        
        await update.message.reply_text(
            "✅ Base de datos guardada.\n\n"
            "Ahora envía tu nombre de usuario de Odoo:"
        )
    
    elif state == "waiting_username":
        user_configs[user_id]['username'] = text
        user_states[user_id] = "waiting_password"
        
        await update.message.reply_text(
            "✅ Usuario guardado.\n\n"
            "Por último, envía tu contraseña de Odoo:"
        )
    
    elif state == "waiting_password":
        user_configs[user_id]['password'] = text
        del user_states[user_id]
        
        await update.message.reply_text(
            "✅ ¡Configuración completada!\n\n"
            "Probando conexión..."
        )
        
        # Probar la conexión
        config = user_configs[user_id]
        odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
        
        if await odoo.authenticate():
            employee_id = await odoo.get_employee_id()
            if employee_id:
                await update.message.reply_text(
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
                await update.message.reply_text(
                    "⚠️ Conexión exitosa pero no se encontró un empleado asociado a tu usuario.\n"
                    "Verifica que tu usuario de Odoo esté vinculado a un empleado."
                )
        else:
            await update.message.reply_text(
                "❌ Error de conexión. Verifica tus credenciales y usa /config para reconfigurar."
            )
            del user_configs[user_id]

async def scheduled_check_in():
    """Tarea programada para marcar entrada (8:00 AM)"""
    logger.info("Ejecutando marcado automático de entrada...")
    
    for user_id, config in user_configs.items():
        try:
            odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
            
            if await odoo.authenticate():
                employee_id = await odoo.get_employee_id()
                if employee_id:
                    if await odoo.create_attendance(employee_id):
                        logger.info(f"Entrada marcada para usuario {user_id}")
                        # Aquí podrías enviar un mensaje al usuario confirmando
                    else:
                        logger.error(f"Error marcando entrada para usuario {user_id}")
                else:
                    logger.error(f"No se encontró empleado para usuario {user_id}")
            else:
                logger.error(f"Error de autenticación para usuario {user_id}")
                
        except Exception as e:
            logger.error(f"Error en entrada automática para usuario {user_id}: {e}")

async def scheduled_check_out():
    """Tarea programada para marcar salida"""
    logger.info("Ejecutando marcado automático de salida...")
    
    for user_id, config in user_configs.items():
        try:
            odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
            
            if await odoo.authenticate():
                employee_id = await odoo.get_employee_id()
                if employee_id:
                    if await odoo.close_attendance(employee_id):
                        logger.info(f"Salida marcada para usuario {user_id}")
                        # Aquí podrías enviar un mensaje al usuario confirmando
                    else:
                        logger.error(f"Error marcando salida para usuario {user_id}")
                else:
                    logger.error(f"No se encontró empleado para usuario {user_id}")
            else:
                logger.error(f"Error de autenticación para usuario {user_id}")
                
        except Exception as e:
            logger.error(f"Error en salida automática para usuario {user_id}: {e}")

async def check_attendance_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verificar si hay asistencia abierta y desde qué hora"""
    user_id = update.effective_user.id
    
    if user_id not in user_configs:
        await update.message.reply_text("❌ No tienes configuración guardada. Usa /config para configurar.")
        return
    
    await update.message.reply_text("🔄 Verificando estado de asistencia...")
    
    config = user_configs[user_id]
    odoo = OdooAPI(config['url'], config['db'], config['username'], config['password'])
    
    if await odoo.authenticate():
        employee_id = await odoo.get_employee_id()
        if employee_id:
            open_attendance = await odoo.get_open_attendance(employee_id)
            if open_attendance:
                # Convertir la fecha/hora de Odoo a zona horaria de Cuba
                check_in_str = open_attendance['check_in']
                # Odoo guarda en UTC, convertir a Cuba
                check_in_utc = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')
                check_in_utc = pytz.utc.localize(check_in_utc)
                check_in_cuba = check_in_utc.astimezone(CUBA_TZ)
                
                await update.message.reply_text(
                    f"✅ Tienes una asistencia abierta\n\n"
                    f"🕐 Hora de entrada: {check_in_cuba.strftime('%H:%M:%S')}\n"
                    f"📅 Fecha: {check_in_cuba.strftime('%d/%m/%Y')}\n"
                    f"⏱️ Tiempo trabajado: {datetime.now(CUBA_TZ) - check_in_cuba}"
                )
            else:
                await update.message.reply_text(
                    "❌ No tienes ninguna asistencia abierta\n\n"
                    "Puedes marcar entrada con /manual_in"
                )
        else:
            await update.message.reply_text("❌ No se encontró empleado asociado.")
    else:
        await update.message.reply_text("❌ Error de conexión.")

def main():
    """Función principal"""
    # Crear aplicación
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Agregar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("config", config))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("test", test_connection))
    application.add_handler(CommandHandler("manual_in", manual_in))
    application.add_handler(CommandHandler("manual_out", manual_out))
    application.add_handler(CommandHandler("check_status", check_attendance_status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
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
    
    # Ejecutar bot
    logger.info("Bot iniciado")
    application.run_polling()

if __name__ == '__main__':
    main()
