import os
import logging
from flask import Flask, jsonify

logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check para keep-alive"""
    return jsonify({
        'status': 'ok',
        'message': 'Bot is running',
        'service': 'telegram-odoo-bot'
    }), 200

@app.route('/', methods=['GET'])
def root():
    """Endpoint raíz"""
    return jsonify({
        'message': 'Telegram Odoo Bot is running',
        'endpoints': ['/health']
    }), 200

def run_web_server():
    """Ejecutar el servidor web"""
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Iniciando servidor web en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
