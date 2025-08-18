import logging
import requests
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
    
    def get_partner_id(self):
        """Obtener el partner_id del usuario autenticado"""
        try:
            search_url = f"{self.url}/web/dataset/call_kw"
            search_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "res.users",
                    "method": "read",
                    "args": [self.uid],
                    "kwargs": {
                        "fields": ["partner_id"],
                        "context": {}
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
                logger.error(f"Error obteniendo partner_id: {result['error']}")
                return None
            
            user_data = result.get('result', [])
            if user_data and user_data[0].get('partner_id'):
                partner_id = user_data[0]['partner_id'][0]
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
            
            search_url = f"{self.url}/web/dataset/call_kw"
            search_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "hr.employee",
                    "method": "search_read",
                    "args": [[["work_contact_id", "=", partner_id]]],
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
            create_url = f"{self.url}/web/dataset/call_kw"
            create_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "hr.attendance",
                    "method": "create",
                    "args": [{
                        "employee_id": employee_id,
                        "check_in": datetime.now(cuba_tz).strftime('%Y-%m-%d %H:%M:%S')
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
            cuba_tz = pytz.timezone('America/Havana')
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
                        {"check_out": datetime.now(cuba_tz).strftime('%Y-%m-%d %H:%M:%S')}
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
