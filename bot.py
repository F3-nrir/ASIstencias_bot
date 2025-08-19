import os
import logging
import threading
import pytz
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram_bot import TelegramBot
from handlers import (
    handle_start, handle_config, handle_status, handle_test,
    handle_manual_in, handle_manual_out, handle_check_status, handle_exit, handle_message
)
from scheduler import scheduled_check_in, scheduled_check_out
from web_server import run_web_server
from keep_alive import KeepAlive

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CUBA_TZ = pytz.timezone('America/Havana')

ALLOWED_USERS = []  # Agregar user_ids aquí: [123456789, 987654321]

def clear_pending_updates(bot):
    """Limpia todos los mensajes pendientes en la cola de Telegram"""
    try:
        logger.info("Limpiando mensajes pendientes...")
        updates = bot.get_updates()
        
        if updates and updates.get('ok'):
            result = updates.get('result', [])
            if result:
                last_update_id = result[-1]['update_id']
                # Confirmar que se procesaron todos los mensajes
                bot.offset = last_update_id + 1
                updates = bot.get_updates()
                logger.info(f"Limpiados {len(result)} mensajes pendientes. Nuevo offset: {bot.offset}")
            else:
                logger.info("No hay mensajes pendientes")
        else:
            logger.info("No se pudieron obtener updates para limpiar")
    except Exception as e:
        logger.error(f"Error limpiando mensajes pendientes: {e}")

def is_user_allowed(user_id):
    """Verifica si el usuario está permitido"""
    if not ALLOWED_USERS:
        from handlers import user_configs
        if len(user_configs) < 2:
            return True
        return user_id in user_configs
    return user_id in ALLOWED_USERS

def main():
    """Función principal"""
    bot = TelegramBot(BOT_TOKEN)
    
    clear_pending_updates(bot)
    time.sleep(2)  # Esperar un poco antes de continuar
    clear_pending_updates(bot)  # Segunda limpieza para asegurar
    
    from handlers import user_configs, user_states
    user_configs.clear()
    user_states.clear()
    logger.info("Datos de usuarios limpiados al inicio")
    
    web_server_thread = threading.Thread(target=run_web_server, daemon=True)
    web_server_thread.start()
    logger.info("Servidor web iniciado en hilo separado")
    
    keep_alive = KeepAlive()
    keep_alive.start_keep_alive()
    
    # Configurar scheduler
    scheduler = BlockingScheduler(timezone=CUBA_TZ)
    
    scheduler.add_job(
        scheduled_check_in,
        CronTrigger(hour=8, minute=0, day_of_week='mon-fri', timezone=CUBA_TZ),
        id='check_in'
    )
    
    scheduler.add_job(
        scheduled_check_out,
        CronTrigger(hour=17, minute=30, day_of_week='mon-thu', timezone=CUBA_TZ),
        id='check_out_weekdays'
    )
    
    scheduler.add_job(
        scheduled_check_out,
        CronTrigger(hour=16, minute=30, day_of_week='fri', timezone=CUBA_TZ),
        id='check_out_friday'
    )
    
    def run_scheduler():
        scheduler.start()
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Scheduler iniciado en hilo separado")
    
    logger.info("Bot iniciado")
    
    while True:
        try:
            updates = bot.get_updates()
            
            if updates and updates.get('ok'):
                result = updates.get('result', [])
                
                last_update_id = None
                
                for update in result:
                    update_id = update['update_id']
                    last_update_id = update_id
                    
                    if 'message' in update:
                        message = update['message']
                        chat_id = message['chat']['id']
                        user_id = message['from']['id']
                        
                        if not is_user_allowed(user_id):
                            bot.send_message(chat_id, "❌ Lo siento, este bot está limitado a usuarios autorizados.")
                            continue
                        
                        if 'text' in message:
                            text = message['text']
                            
                            try:
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
                                elif text == '/exit':
                                    handle_exit(bot, chat_id, user_id)
                                elif not text.startswith('/'):
                                    handle_message(bot, chat_id, user_id, text)
                            except Exception as e:
                                logger.error(f"Error procesando mensaje: {e}")
                
                if last_update_id is not None:
                    bot.offset = last_update_id + 1
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error en loop principal: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
