# Bot de Telegram para Asistencias Odoo

Este bot permite marcar automáticamente las asistencias en Odoo 16 a través de Telegram.

## Características

- ✅ Configuración inicial de conexión a Odoo
- ⏰ Marcado automático de entrada a las 8:00 AM
- ⏰ Marcado automático de salida (5:30 PM L-J, 4:30 PM V)
- 🔧 Comandos manuales para marcar entrada/salida
- 🌍 Zona horaria de Cuba
- 🔒 Seguridad: cada usuario solo puede marcar sus propias asistencias

## Comandos disponibles

- `/start` - Iniciar el bot
- `/config` - Configurar conexión a Odoo
- `/status` - Ver configuración actual
- `/test` - Probar conexión con Odoo
- `/manual_in` - Marcar entrada manual
- `/manual_out` - Marcar salida manual

## Configuración inicial

1. Envía `/start` al bot
2. Usa `/config` para configurar:
   - URL del servidor Odoo
   - Nombre de la base de datos
   - Usuario de Odoo
   - Contraseña de Odoo

## Horarios automáticos

- **Lunes a Jueves**: 8:00 AM - 5:30 PM
- **Viernes**: 8:00 AM - 4:30 PM
- **Zona horaria**: Cuba (America/Havana)

## Requisitos en Odoo

- Odoo 16
- Módulo `hr_attendance_mobile` instalado
- Usuario con permisos de "Kiosk" en asistencias
- Usuario vinculado a un empleado

## Despliegue en Render.com

1. Sube el código a un repositorio de GitHub
2. Conecta el repositorio en Render.com
3. El bot se ejecutará automáticamente
