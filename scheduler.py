import logging
from handlers import user_configs
from odoo_api import OdooAPI

logger = logging.getLogger(__name__)

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
