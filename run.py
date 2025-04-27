from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import logging
import json # Needed for ML data formatting
import datetime
from index import create_app, db # Assuming index.py contains create_app and db setup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()
backend_url = "https://flask-blog-m8jl.onrender.com" # Your app's own URL

# !!! IMPORTANT: Use a strong, unique secret key and store it securely (e.g., environment variable) !!!
# This key MUST match the EXTENSION_SECRET_KEY in background.js
EXTENSION_SECRET = "aK8$!zPq9*wJv7@rGx3#sF5&dN" # <--- CHANGE THIS!

# URL for your ML prediction server (running on ngrok/localhost)
ML_PREDICTION_URL = "https://025b-106-76-160-228.ngrok-free.app/predict_result" #<--- Use the URL from background.js constants

# Global variable for tracking active users (simplistic approach - see notes below)
# WARNING: This is NOT reliable in production with multiple workers (like gunicorn on Render).
# Each worker process will have its own independent count.
# Consider using a shared store like Redis or a database for accurate tracking.
active_users = 0

# --- ML Prediction Trigger Logic ---
def format_data_for_ml_model(user_count):
    """
    Formats data into a dictionary suitable for sending as JSON to the ML model endpoint.
    Matches the required features: active_users, request_rate, response_time_avg, hour, day_of_week.
    """
    logger.info("Formatting data for ML model...")

    # Get current time components
    now = datetime.datetime.now()
    current_hour = now.hour
    current_day_of_week = now.weekday() # Note: Monday is 0, Sunday is 6

    # --- Placeholders for currently untracked metrics ---
    # TODO: Implement proper backend tracking for request_rate and response_time_avg
    request_rate_placeholder = 0.0
    response_time_avg_placeholder = 0.0
    # --- End Placeholders ---

    # Assemble the data into a dictionary matching expected feature names
    # This dictionary will be sent as JSON to the ML server.
    ml_data = {
        "active_users": user_count if user_count is not None else 0, # Handle potential None for safety
        "request_rate": request_rate_placeholder,
        "response_time_avg": response_time_avg_placeholder,
        "hour": current_hour,
        "day_of_week": current_day_of_week
    }

    logger.info(f"Formatted ML Input Data (as dict): {ml_data}")
    return ml_data # Return the dictionary


def check_users_and_predict():
    """Checks user count and triggers ML prediction if count > 5."""
    global active_users
    logger.info(f"Checking user count for prediction. Current count (this worker): {active_users}")

    # Use the global count (acknowledging limitations)
    if active_users > 5:
        logger.info(f"User count ({active_users}) > 5. Triggering prediction.")
        try:
            # Get the data formatted as a dictionary
            ml_input_data_dict = format_data_for_ml_model(active_users)

            # Send the dictionary as JSON payload using the 'json' parameter
            logger.info(f"Sending POST to ML Server: {ML_PREDICTION_URL}")
            response = requests.post(
                ML_PREDICTION_URL,
                json=ml_input_data_dict, # Send the dictionary as JSON
                timeout=15
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            logger.info(f"Prediction request successful. ML server response: {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
             logger.error(f"Timeout error sending prediction request to {ML_PREDICTION_URL}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending prediction request to ML server: {e}")
        except Exception as e:
             logger.error(f"Unexpected error during prediction trigger: {e}", exc_info=True) # Include traceback
    else:
         logger.info(f"User count ({active_users}) <= 5. No prediction triggered.")

# ... (Keep the rest of your run.py code: scheduler, endpoints, app.run) ...

# Make sure the check_users_and_predict() function is called appropriately
# (e.g., in user_enter, user_exit, or potentially periodically)


# --- Endpoints ---

# Scheduler to keep Render free tier alive (optional)
def restart_server():
    logger.info('Ping task running to keep server alive.')
    try:
        response = requests.get(backend_url) # Ping itself
        if response.status_code == 200:
            logger.info("Server ping successful.")
        else:
            logger.error(f"Server ping failed. Status code: {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Error during server ping: {str(e)}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=restart_server, trigger="interval", minutes=10) # Reduced interval slightly
scheduler.start()

# The traffic API endpoint (receives detailed data from extension)
@app.route('/api/traffic', methods=['POST'])
def handle_traffic():
    # Check secret key from extension
    secret = request.headers.get('X-Extension-Secret')
    if secret != EXTENSION_SECRET:
        logger.warning(f"Unauthorized access attempt to /api/traffic. Provided key: {secret}")
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    if not data:
         logger.error("Received empty or non-JSON data for /api/traffic")
         return jsonify({'error': 'Bad Request - Missing JSON data'}), 400

    logger.info(f"Received traffic data via /api/traffic: {data}")

    # Process the received data (e.g., store it in DB, analyze it)
    # Example: Log the session ID and type of data
    session_id = data.get('sessionId', 'N/A')
    data_type = data.get('type', 'N/A')
    logger.info(f"Traffic details: Session={session_id}, Type={data_type}")

    # You could potentially trigger the prediction check here too,
    # based on incoming data, but it's already called on user enter/exit.
    # check_users_and_predict()

    # Send response back to extension
    return jsonify({'status': 'success', 'message': 'Traffic data received'}), 200

# Endpoint called by extension when a monitored tab is opened/navigated to
@app.route('/api/user_enter', methods=['POST'])
def user_enter():
    global active_users
    active_users += 1
    logger.info(f"User entered (called by extension). Active users now (this worker): {active_users}")
    # Trigger prediction check whenever count changes
    check_users_and_predict()
    return jsonify({"message": "User entered", "active_users": active_users}), 200

# Endpoint called by extension when a monitored tab is closed/navigated away from
@app.route('/api/user_exit', methods=['POST'])
def user_exit():
    global active_users
    # Prevent count from going negative if multiple requests arrive somehow
    if active_users > 0:
        active_users -= 1
    else:
         active_users = 0 # Ensure it doesn't go below zero
    logger.info(f"User exited (called by extension). Active users now (this worker): {active_users}")
    # Trigger prediction check whenever count changes
    check_users_and_predict()
    return jsonify({"message": "User exited", "active_users": active_users}), 200

# Endpoint for the extension to fetch the current (potentially inaccurate) count
@app.route('/api/get_live_users', methods=['GET'])
def get_live_users():
    # This endpoint returns the potentially inaccurate global count.
    # No authentication needed here based on current setup.
    global active_users
    logger.info(f"Providing live user count (this worker): {active_users}")
    return jsonify({"active_users": active_users}), 200

# --- App Initialization ---
# Ensure DB setup happens within app context if needed elsewhere
# with app.app_context():
#     db.create_all() # Only if you are using Flask-SQLAlchemy and need tables created

if __name__ == "__main__":
    # use_reloader=False is important when using APScheduler in debug mode
    # Set host='0.0.0.0' to be accessible externally if not using a production server like gunicorn
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)