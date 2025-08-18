import logging
import pytz
from datetime import datetime
from odoo_api import OdooAPI

logger = logging.getLogger(__name__)

# Almacenamiento temporal de configuraciones de usuario
user_configs = {}
user_states = {}

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
            "/check_status - Ver si tienes asistencia abierta\n"
            "/exit - Borrar configuración y empezar de nuevo"
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
            cuba_tz = pytz.timezone('America/Havana')
            now = datetime.now(cuba_tz)
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
            cuba_tz = pytz.timezone('America/Havana')
            now = datetime.now(cuba_tz)
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
                cuba_tz = pytz.timezone('America/Havana')
                check_in_str = open_attendance['check_in']
                check_in_utc = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')
                check_in_utc = pytz.utc.localize(check_in_utc)
                check_in_cuba = check_in_utc.astimezone(cuba_tz)
                
                text = (
                    f"✅ Tienes una asistencia abierta\n\n"
                    f"🕐 Hora de entrada: {check_in_cuba.strftime('%H:%M:%S')}\n"
                    f"📅 Fecha: {check_in_cuba.strftime('%d/%m/%Y')}\n"
                    f"⏱️ Tiempo trabajado: {datetime.now(cuba_tz) - check_in_cuba}"
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

def handle_exit(bot, chat_id, user_id):
    """Borrar configuración del usuario y detener tareas programadas"""
    if user_id not in user_configs:
        bot.send_message(chat_id, "❌ No tienes configuración guardada.")
        return
    
    # Borrar configuración del usuario
    del user_configs[user_id]
    
    # Borrar estado si existe
    if user_id in user_states:
        del user_states[user_id]
    
    text = (
        "🗑️ Configuración eliminada exitosamente.\n\n"
        "✅ Tus tareas programadas han sido detenidas.\n"
        "✅ Todos tus datos han sido borrados.\n\n"
        "Puedes usar /start para comenzar de nuevo."
    )
    
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
                    "/test - Probar conexión\n"
                    "/exit - Borrar configuración y empezar de nuevo"
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
