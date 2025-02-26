from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import logging
from index import create_app, db
from flask import request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

backend_url = "https://flask-blog-m8jl.onrender.com"

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

#The traffic API endpoint
@app.route('/api/traffic', methods=['POST'])
def handle_traffic():
    secret = request.headers.get('X-Extension-Secret')
    if secret != 'YOUR_SECRET_KEY':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    # Log received traffic data
    logger.info(f"Received traffic data: {data}")
    
    # Process and store data for ML model
    # You can add your data processing logic here
    
    # Return alerts if needed
    return jsonify({'status': 'success', 'alert': False})


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)