"""A test of a flask webhook interface with zotero, with dialog buttons that popup if the file the 
listener wants to generate already exists.  The only way to do this in a decent way in python was to
popup the dialog in a browser, unfortunately.  The exruciating details are here:

https://www.perplexity.ai/search/the-javascript-below-is-intend-Tic7.jP4TQiZ6R9CAl9EBQ

The companion javascript for this goes in zotero action and tags plugin. and is multikey_sender_test.js"""

from flask import Flask, request, jsonify, render_template_string, redirect
import logging
import json
from datetime import datetime
import time
import threading
from pathlib import Path
import sys
import os
import uuid
import webbrowser

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("zotero_watcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# For icecream debugging if available
try:
    from icecream import ic
except ImportError:
    def ic(*args, **kwargs):
        pass

# Create Flask app
app = Flask(__name__)

# Create storage directory path
STORAGE_DIR = Path("~/tmp/zotero_items").expanduser()
LISTEN_PORT = 5050

# Create lock for synchronization
dir_lock = threading.Lock()

# Dictionary to store dialog results
dialog_results = {}
dialog_events = {}

# HTML template for the dialog
DIALOG_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
            max-width: 500px;
            margin: 0 auto;
        }
        .message {
            margin-bottom: 20px;
        }
        .buttons {
            display: flex;
            gap: 10px;
        }
        button {
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .overwrite {
            background-color: #4CAF50;
            color: white;
        }
        .skip {
            background-color: #f44336;
            color: white;
        }
        .skip-all {
            background-color: #ff9800;
            color: white;
        }
    </style>
    <script>
        function submitAndClose(action) {
            // Submit the form via fetch API
            fetch('/dialog-response/{{ dialog_id }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'action=' + action
            })
            .then(response => {
                // Try multiple ways to close the window
                window.close();
                
                // If window is still open, try with a delay
                setTimeout(function() {
                    window.close();
                }, 100);
            })
            .catch(error => {
                console.error('Error:', error);
                // Still try to close the window even if there was an error
                window.close();
            });
            
            // Return false to prevent default form submission
            return false;
        }
    </script>
</head>
<body>
    <div class="message">{{ message }}</div>
    <div class="buttons">
        <button onclick="submitAndClose('overwrite');" class="overwrite">Overwrite</button>
        <button onclick="submitAndClose('cancel');" class="skip">Skip</button>
        {% if show_skip_all %}
        <button onclick="submitAndClose('cancel_all');" class="skip-all">Skip All</button>
        {% endif %}
    </div>
</body>
</html>
"""

def ensure_storage_dir(request_id):
    """
    Ensure the storage directory exists with proper synchronization.
    Returns True if successful, False otherwise.
    """
    with dir_lock:
        if not STORAGE_DIR.exists():
            logger.info(f"[{request_id}] Creating storage directory: {STORAGE_DIR}")
            try:
                STORAGE_DIR.mkdir(parents=True, exist_ok=True)
                # Small delay to ensure directory is fully created and visible to all threads
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"[{request_id}] Error creating directory: {e}")
                return False
        
        # Double-check directory exists
        if not STORAGE_DIR.exists():
            logger.error(f"[{request_id}] Directory does not exist after creation attempt: {STORAGE_DIR}")
            return False
            
        return True

@app.route('/dialog/<dialog_id>')
def show_dialog(dialog_id):
    """Show a dialog in the browser"""
    if dialog_id not in dialog_events:
        return "Dialog not found", 404
        
    dialog_data = dialog_events[dialog_id]
    return render_template_string(
        DIALOG_TEMPLATE,
        title="File Exists",
        message=dialog_data['message'],
        dialog_id=dialog_id,
        show_skip_all=dialog_data.get('show_skip_all', False)
    )

@app.route('/dialog-response/<dialog_id>', methods=['POST'])
def dialog_response(dialog_id):
    """Handle dialog response"""
    if dialog_id not in dialog_events:
        return "Dialog not found", 404
        
    action = request.form.get('action', 'cancel')
    logger.info(f"Dialog {dialog_id} response: {action}")
    
    # Store the result
    dialog_results[dialog_id] = action
    
    # Signal the event to notify the waiting thread
    dialog_events[dialog_id]['event'].set()
    
    # Return success - the browser window should be closed by JavaScript
    return "OK"

def show_web_dialog(title, message, options, request_id):
    """Show a dialog in the browser and wait for response"""
    dialog_id = f"dialog_{uuid.uuid4().hex[:8]}"
    
    # Create an event to wait for the response
    event = threading.Event()
    
    # Store dialog information
    dialog_events[dialog_id] = {
        'title': title,
        'message': message,
        'event': event,
        'show_skip_all': options == 'yesnocancel'
    }
    
    # URL for the dialog
    url = f"http://localhost:{LISTEN_PORT}/dialog/{dialog_id}"
    
    # Open the URL in a browser
    logger.info(f"[{request_id}] Opening dialog in browser: {url}")
    webbrowser.open(url)
    
    # Wait for response with timeout
    if not event.wait(timeout=60):
        logger.warning(f"[{request_id}] Dialog timeout after 60 seconds")
        # Clean up
        if dialog_id in dialog_events:
            del dialog_events[dialog_id]
        return "cancel"  # Default to cancel on timeout
    
    # Get the result
    result = dialog_results.get(dialog_id, "cancel")
    
    # Clean up
    if dialog_id in dialog_results:
        del dialog_results[dialog_id]
    if dialog_id in dialog_events:
        del dialog_events[dialog_id]
    
    return result
def show_overwrite_popup(citekey, is_last_item, total_items, request_id):
    """Display a popup asking whether to overwrite the file"""
    logger.info(f"[{request_id}] Showing overwrite popup for '{citekey}'")
    
    # Simple message for all cases
    message = f"File for citekey '{citekey}' already exists."
    
    # Use our web-based dialog
    result = show_web_dialog(
        "File Exists",
        message,
        "yesno" if (total_items == 1 or is_last_item) else "yesnocancel",
        request_id
    )
    
    logger.info(f"[{request_id}] User selected: {result} for '{citekey}'")
    return result

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Endpoint that receives webhook data from Zotero Tags and Actions plugin.
    Expects a JSON array of objects with itemkey and citekey.
    """
    # Generate a unique ID for this request for traceability
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Received webhook request")
    
    try:
        # Get the JSON data from the request
        data = request.get_json()
        
        if not data:
            logger.error(f"[{request_id}] No data received")
            return jsonify({"status": "error", "message": "No data received"}), 400
            
        if not isinstance(data, list):
            logger.error(f"[{request_id}] Expected JSON array, got {type(data)}: {data}")
            return jsonify({"status": "error", "message": "Expected JSON array"}), 400
        
        logger.info(f"[{request_id}] Processing {len(data)} items")
        ic(data)  # Debug the data
        
        # Ensure storage directory exists before processing
        if not ensure_storage_dir(request_id):
            return jsonify({
                "status": "error", 
                "message": "Failed to create storage directory",
                "request_id": request_id
            }), 500
        
        # Process the received items
        results = process_items(data, request_id)
        
        logger.info(f"[{request_id}] Completed processing with {len(results)} results")
        return jsonify({
            "status": "success", 
            "processed": len(results),
            "items": results,
            "request_id": request_id
        })
        
    except Exception as e:
        logger.exception(f"[{request_id}] Error processing webhook data: {str(e)}")
        return jsonify({"status": "error", "message": str(e), "request_id": request_id}), 500

def process_items(items, request_id):
    """
    Process Zotero items received from the webhook using EAFP approach.
    
    Args:
        items (list): List of dictionaries with itemkey and citekey
        request_id (str): Unique ID for this request
        
    Returns:
        list: Results of processing each item
    """
    cancel_all = False
    results = []
    
    logger.info(f"[{request_id}] Starting to process {len(items)} Zotero items")
    total_items = len(items)
    
    # Ensure storage directory exists first
    if not ensure_storage_dir(request_id):
        logger.error(f"[{request_id}] Could not ensure storage directory exists")
        return []
    
    for index, item in enumerate(items):
        if cancel_all:
            logger.info(f"[{request_id}] Skipping remaining items due to 'cancel all' selection")
            break
            
        # Extract keys from the item
        itemkey = item.get('itemkey')
        citekey = item.get('citekey')
        
        if not itemkey or not citekey:
            logger.warning(f"[{request_id}] Missing required keys in item: {item}")
            continue
        
        logger.info(f"[{request_id}] Processing item {index+1}/{total_items}: {citekey}")
        
        # Create filepath using pathlib
        filename = f"{citekey}.json"
        filepath = STORAGE_DIR / filename
        is_last_item = (index == total_items - 1)
        
        # Log the file path we're checking
        logger.debug(f"[{request_id}] Checking existence of: {filepath.resolve()}")
        
        # Using EAFP approach with atomic file creation
        try:
            # Try to open the file in 'x' mode which fails if file exists
            logger.debug(f"[{request_id}] Attempting to create file exclusively: {filepath}")
            with open(filepath, 'x') as f:
                # File created successfully, write the contents
                json_content = json.dumps(item, indent=2)
                f.write(json_content)
                logger.info(f"[{request_id}] Successfully created new file: {filepath}")
                
                # Process the item
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Record the result
                results.append({
                    "itemkey": itemkey,
                    "citekey": citekey,
                    "timestamp": timestamp,
                    "filepath": str(filepath)
                })
                
                logger.info(f"[{request_id}] Processed item: {citekey} (Zotero key: {itemkey})")
            
        except FileExistsError:
            # File already exists, show popup
            logger.info(f"[{request_id}] File already exists (caught exception): {filepath}")
            
            # Show the popup
            action = show_overwrite_popup(citekey, is_last_item, total_items, request_id)
            
            if action == "cancel":
                logger.info(f"[{request_id}] Skipping file: {filepath}")
                continue
            elif action == "cancel_all":
                logger.info(f"[{request_id}] Cancelling all remaining operations")
                cancel_all = True
                continue
            
            # User chose to overwrite, write to the file
            try:
                logger.debug(f"[{request_id}] Overwriting file: {filepath}")
                with open(filepath, 'w') as f:
                    json_content = json.dumps(item, indent=2)
                    f.write(json_content)
                logger.info(f"[{request_id}] Successfully overwrote file: {filepath}")
                
                # Process the item
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Record the result
                results.append({
                    "itemkey": itemkey,
                    "citekey": citekey,
                    "timestamp": timestamp,
                    "filepath": str(filepath)
                })
                
                logger.info(f"[{request_id}] Processed item: {citekey} (Zotero key: {itemkey})")
            except Exception as e:
                logger.error(f"[{request_id}] Error overwriting file: {e}", exc_info=True)
                continue
                
        except Exception as e:
            # Other errors during file writing
            logger.error(f"[{request_id}] Error writing file: {e}", exc_info=True)
            continue
    
    return results

@app.route('/status', methods=['GET'])
def status():
    """Simple endpoint to verify the server is running"""
    # First ensure storage directory exists
    if not STORAGE_DIR.exists():
        return jsonify({
            "status": "running",
            "time": datetime.now().isoformat(),
            "storage_dir": str(STORAGE_DIR),
            "storage_exists": False,
            "files_in_dir": []
        })
    
    # Get files if directory exists
    try:
        files_list = [f.name for f in STORAGE_DIR.iterdir() if f.is_file()]
    except Exception as e:
        files_list = [f"Error listing files: {str(e)}"]
        
    return jsonify({
        "status": "running",
        "time": datetime.now().isoformat(),
        "storage_dir": str(STORAGE_DIR),
        "storage_exists": True,
        "files_in_dir": files_list,
        "active_dialogs": list(dialog_events.keys())
    })

if __name__ == '__main__':
    log_file = Path("zotero_watcher.log")
    logger.info(f"Starting Zotero Lit Note Watcher")
    logger.info(f"Storage directory path: {STORAGE_DIR}")
    logger.info(f"Log file: {log_file.resolve()}")
    
    # Create storage directory at startup
    try:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Storage directory exists or was created successfully")
    except Exception as e:
        logger.warning(f"Note: Could not create storage directory at startup: {e}")
    
    # Start Flask server
    logger.info(f"Starting server on port {LISTEN_PORT}")
    app.run(host='localhost', port=LISTEN_PORT, debug=False, threaded=True)
