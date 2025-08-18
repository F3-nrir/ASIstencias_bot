# Guía de Despliegue en Render.com

## Paso a paso para desplegar el bot

### 1. Preparar el código

1. Crea un repositorio en GitHub
2. Sube todos los archivos del bot al repositorio:
   - `bot.py`
   - `requirements.txt`
   - `render.yaml`
   - `README.md`
   - `.env.example` (para referencia)

### 2. Configurar Render.com

1. Ve a [render.com](https://render.com) y crea una cuenta
2. Haz clic en "New +" y selecciona "Web Service"
3. Conecta tu repositorio de GitHub
4. Configura el servicio:
   - **Name**: `telegram-odoo-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`

### 3. Variables de entorno (RECOMENDADO)

Para mayor seguridad, configura el token como variable de entorno:

1. En la configuración del servicio en Render, ve a "Environment"
2. Agrega la variable:
   - **Key**: `TELEGRAM_BOT_TOKEN`
   - **Value**: `token` (o tu token personalizado)

**¿Por qué usar variables de entorno?**
- ✅ Mayor seguridad: el token no queda expuesto en el código
- ✅ Fácil cambio de tokens sin modificar código
- ✅ Buenas prácticas de desarrollo

### 4. Desplegar

1. Haz clic en "Create Web Service"
2. Render automáticamente:
   - Clonará tu repositorio
   - Instalará las dependencias
   - Iniciará el bot

### 5. Verificar funcionamiento

1. Ve a los logs en Render para verificar que el bot inició correctamente
2. Busca tu bot en Telegram: `@tu_bot_name`
3. Envía `/start` para probar

## Notas importantes

- El bot se ejecuta 24/7 en Render
- Los horarios están configurados para la zona horaria de Cuba
- Render tiene un plan gratuito con 750 horas/mes
- Para producción, considera el plan de pago para mayor estabilidad

## Solución de problemas

### Bot no responde
- Verifica los logs en Render
- Confirma que el token del bot es correcto (revisa la variable de entorno)
- Asegúrate de que el bot esté iniciado con BotFather

### Error de conexión a Odoo
- Verifica que la URL de Odoo sea accesible desde internet
- Confirma que el módulo `hr_attendance_mobile` esté instalado
- Verifica que el usuario tenga permisos de kiosk

### Horarios no funcionan
- Los logs mostrarán si las tareas programadas se ejecutan
- Verifica la zona horaria en los logs
- Confirma que hay usuarios configurados

### Error de variables de entorno
- Si el bot no inicia, verifica que `TELEGRAM_BOT_TOKEN` esté configurado correctamente
- Los logs mostrarán si hay problemas con las variables de entorno

## Mantenimiento

- Los logs se pueden ver en tiempo real en Render
- El bot se reinicia automáticamente si hay errores
- Las configuraciones de usuario se pierden al reiniciar (considera usar una base de datos para producción)
- Para cambiar el token, solo modifica la variable de entorno en Render (no necesitas tocar el código)
