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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CUBA_TZ = pytz.timezone('America/Havana')

def main():
    """Función principal"""
    bot = TelegramBot(BOT_TOKEN)
    
    # Configurar scheduler
    scheduler = BlockingScheduler(timezone=CUBA_TZ)
    
    # Entrada a las 8:00 AM, lunes a viernes
    scheduler.add_job(
        scheduled_check_in,
        CronTrigger(hour=8, minute=0, day_of_week='mon-fri', timezone=CUBA_TZ),
        id='check_in'
    )
    
    # Salida a las 5:30 PM, lunes a jueves
    scheduler.add_job(
        scheduled_check_out,
        CronTrigger(hour=17, minute=30, day_of_week='mon-thu', timezone=CUBA_TZ),
        id='check_out_weekdays'
    )
    
    # Salida a las 4:30 PM, viernes
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
                            elif text == '/exit':
                                handle_exit(bot, chat_id, user_id)
                            elif not text.startswith('/'):
                                handle_message(bot, chat_id, user_id, text)
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error en loop principal: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
