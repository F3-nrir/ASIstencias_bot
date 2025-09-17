import logging
import xmlrpc.client
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class OdooAPI:
    def __init__(self, url, db, username, password):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.models = None
    
    def authenticate(self):
        """Autenticar con Odoo usando xmlrpc"""
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            
            if self.uid:
                self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
                logger.info(f"Autenticación exitosa. UID: {self.uid}")
                return True
            else:
                logger.error("Credenciales inválidas")
                return False
                
        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return False
    
    def get_partner_id(self):
        """Obtener el partner_id del usuario autenticado"""
        try:
            user = self.models.execute_kw(self.db, self.uid, self.password, 
                                        'res.users', 'read', [self.uid], 
                                        {'fields': ['partner_id']})
            
            if user and user[0].get('partner_id'):
                partner_id = user[0]['partner_id'][0]
                logger.info(f"Partner ID obtenido: {partner_id}")
                return partner_id
            else:
                logger.error("No se pudo obtener partner_id del usuario")
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo partner_id: {e}")
            return None
    
    def get_employee_id(self):
        """Obtener el ID del empleado asociado al partner_id del usuario"""
        try:
            partner_id = self.get_partner_id()
            if not partner_id:
                return None
            
            employees = self.models.execute_kw(self.db, self.uid, self.password,
                                             'hr.employee', 'search_read',
                                             [[['work_contact_id', '=', partner_id]]],
                                             {'fields': ['id', 'name']})
            
            if employees:
                employee_id = employees[0]['id']
                logger.info(f"Empleado encontrado: {employees[0]['name']} (ID: {employee_id})")
                return employee_id
            else:
                logger.error("No se encontró empleado asociado al partner_id")
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo empleado: {e}")
            return None
    
    def create_attendance(self, employee_id):
        """Crear registro de asistencia (entrada)"""
        try:
            cuba_tz = pytz.timezone('America/Havana')
            attendance_id = self.models.execute_kw(self.db, self.uid, self.password,
                                                 'hr.attendance', 'create',
                                                 [{
                                                     'employee_id': employee_id,
                                                     'check_in': datetime.now(cuba_tz).strftime('%Y-%m-%d %H:%M:%S')
                                                 }])
            
            logger.info(f"Asistencia creada exitosamente. ID: {attendance_id}")
            return True
                
        except Exception as e:
            logger.error(f"Error creando asistencia: {e}")
            return False
    
    def close_attendance(self, employee_id):
        """Cerrar registro de asistencia abierto (salida)"""
        try:
            cuba_tz = pytz.timezone('America/Havana')
            attendances = self.models.execute_kw(self.db, self.uid, self.password,
                                               'hr.attendance', 'search_read',
                                               [[['employee_id', '=', employee_id],
                                                 ['check_out', '=', False]]],
                                               {'fields': ['id'], 'limit': 1})
            
            if not attendances:
                logger.warning("No hay asistencia abierta para cerrar")
                return False
            
            attendance_id = attendances[0]['id']
            self.models.execute_kw(self.db, self.uid, self.password,
                                 'hr.attendance', 'write',
                                 [[attendance_id], 
                                  {'check_out': datetime.now(cuba_tz).strftime('%Y-%m-%d %H:%M:%S')}])
            
            logger.info(f"Asistencia cerrada exitosamente. ID: {attendance_id}")
            return True
                
        except Exception as e:
            logger.error(f"Error cerrando asistencia: {e}")
            return False
    
    def get_open_attendance(self, employee_id):
        """Obtener asistencia abierta del empleado"""
        try:
            attendances = self.models.execute_kw(self.db, self.uid, self.password,
                                               'hr.attendance', 'search_read',
                                               [[['employee_id', '=', employee_id],
                                                 ['check_out', '=', False]]],
                                               {'fields': ['id', 'check_in'], 'limit': 1})
            
            if attendances:
                return attendances[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo asistencia abierta: {e}")
            return None

    def get_last_attendance(self, employee_id):
        """Obtener la última asistencia del empleado (abierta o cerrada)"""
        try:
            attendances = self.models.execute_kw(self.db, self.uid, self.password,
                                               'hr.attendance', 'search_read',
                                               [[['employee_id', '=', employee_id]]],
                                               {'fields': ['id', 'check_in', 'check_out'], 
                                                'order': 'id desc', 
                                                'limit': 1})
            
            if attendances:
                return attendances[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo última asistencia: {e}")
            return None