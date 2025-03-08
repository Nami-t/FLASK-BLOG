from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import logging
from index import create_app, db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()
backend_url = "https://flask-blog-m8jl.onrender.com"

# Global variable for tracking active users
active_users = 0

def restart_server():
    logger.info('Attempting to restart server')
    try:
        response = requests.get(backend_url)
        if response.status_code == 200:
            logger.info("Server restarted successfully")
        else:
            logger.error(f"Failed to restart server. Status code: {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Error during restart: {str(e)}")

# Set up the scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=restart_server, trigger="interval", minutes=14)
scheduler.start()

# The traffic API endpoint
@app.route('/api/traffic', methods=['POST'])
def handle_traffic():
    secret = request.headers.get('X-Extension-Secret')
    if secret != 'YOUR_SECRET_KEY':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    logger.info(f"Received traffic data: {data}")
    
    return jsonify({'status': 'success', 'alert': False})

# Endpoint to track when a user opens a new tab
@app.route('/api/user_enter', methods=['POST'])
def user_enter():
    global active_users
    active_users += 1
    logger.info(f"User entered. Active users: {active_users}")
    return jsonify({"message": "User entered", "active_users": active_users})

# Endpoint to track when a user closes a tab
@app.route('/api/user_exit', methods=['POST'])
def user_exit():
    global active_users
    if active_users > 0:
        active_users -= 1
    logger.info(f"User exited. Active users: {active_users}")
    return jsonify({"message": "User exited", "active_users": active_users})

# Endpoint to get the current active user count
@app.route('/api/get_live_users', methods=['GET'])
def get_live_users():
    return jsonify({"active_users": active_users})

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
