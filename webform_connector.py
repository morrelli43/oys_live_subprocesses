"""
Web Form connector for collecting contacts.
"""
from typing import List
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime, timezone
import json
import os

import threading

from contact_model import Contact

class WebFormConnector:
    """Simple web form to collect contacts."""
    
    def __init__(self, storage_file: str = 'webform_contacts.json'):
        self.storage_file = storage_file
        self.app = Flask(__name__)
        self.engine = None
        CORS(self.app)  # Enable CORS for all routes
        self._setup_routes()
        self._load_contacts()

    def _trigger_sync(self):
        """Run sync in background thread."""
        if self.engine:
            print("Triggering background sync...")
            try:
                # Run sync in a way that doesn't print too much noise if possible,
                # or just let it log standard output
                self.engine.sync_all()
            except Exception as e:
                print(f"Background sync failed: {e}")
    
    def _load_contacts(self):
        """Load contacts from storage file."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    self.stored_contacts = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse {self.storage_file}: {e}")
                print("Starting with empty contact list.")
                self.stored_contacts = []
        else:
            self.stored_contacts = []
    
    def _save_contacts(self):
        """Save contacts to storage file."""
        with open(self.storage_file, 'w') as f:
            json.dump(self.stored_contacts, f, indent=2)
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Render contact submission form."""
            return render_template_string(CONTACT_FORM_HTML)
        
        @self.app.route('/submit', methods=['POST'])
        def submit_contact():
            """
            Handle contact form submission.
            Supports both form data and JSON payloads.
            """
            if request.is_json:
                data = request.json
                # Handle list of contacts (as per user spec)
                if isinstance(data, list):
                    # Process each contact in the list
                    count = 0
                    for item in data:
                        self._process_contact_data(item)
                        count += 1
                    
                    # Trigger background sync
                    if self.engine:
                        threading.Thread(target=self._trigger_sync).start()
                        
                    return jsonify({'status': 'success', 'message': f'{count} contacts processed successfully!'})
                else:
                    # Process single contact object
                    self._process_contact_data(data)
                    
                    # Trigger background sync
                    if self.engine:
                        threading.Thread(target=self._trigger_sync).start()

                    return jsonify({'status': 'success', 'message': 'Contact processed successfully!'})
            else:
                # Handle standard form submission
                data = request.form
                self._process_contact_data(data)
                
                # Trigger background sync
                if self.engine:
                    threading.Thread(target=self._trigger_sync).start()
                    
                return jsonify({'status': 'success', 'message': 'Contact submitted successfully!'})
        
        @self.app.route('/api/contacts', methods=['GET'])
        def get_contacts():
            """API endpoint to get all contacts."""
            return jsonify({'contacts': self.stored_contacts})

    def _process_contact_data(self, data):
        """Process a single contact data dictionary and save it."""
        # Look for any field containing 'scooter' to be more flexible
        escooter_val = data.get('escooter1') or data.get('escooter')
        if not escooter_val:
            scooter_name = data.get('scooter_name', '')
            scooter_model = data.get('scooter_model', '')
            if scooter_name or scooter_model:
                escooter_val = f"{scooter_name} {scooter_model}".strip()

        contact_data = {
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'phone': data.get('phone', ''),
            'suburb': data.get('suburb', ''), 
            'postcode': data.get('postcode', ''),
            'email': data.get('email', ''),
            'company': data.get('company', ''),
            'notes': data.get('notes', ''),
            'escooter1': escooter_val,
            'timestamp': data.get('timestamp') or datetime.now(timezone.utc).isoformat()
        }
        
        # Capture other escooters if present
        for i in range(2, 4):
            key = f'escooter{i}'
            if key in data:
                contact_data[key] = data[key]
        
        print(f"Processed webform contact: {contact_data.get('first_name')} {contact_data.get('last_name')} - Scooter: {escooter_val}")
        self.stored_contacts.append(contact_data)
        self._save_contacts()
        
        

    
    def fetch_contacts(self) -> List[Contact]:
        """Fetch all contacts from web form storage."""
        self._load_contacts()
        contacts = []
        
        for data in self.stored_contacts:
            contact = Contact()
            contact.first_name = data.get('first_name')
            contact.last_name = data.get('last_name')
            contact.email = data.get('email')
            contact.phone = data.get('phone')
            contact.company = data.get('company')
            contact.notes = data.get('notes')
            
            # Map Suburb and Postcode to Address and set defaults
            address = {
                'city': data.get('suburb', ''),
                'postal_code': data.get('postcode', ''),
                'state': 'Victoria',
                'country': 'Australia'
            }
            if address['city'] or address['postal_code']:
                contact.addresses.append(address)
            
            # Map custom fields
            for key in ['escooter1', 'escooter2', 'escooter3']:
                if data.get(key):
                    contact.extra_fields[key] = data[key]
            
            # Use timestamp as source ID to ensure uniqueness
            if 'timestamp' in data:
                contact.source_ids['webform'] = data['timestamp']
                dt = datetime.fromisoformat(data['timestamp'])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                contact.last_modified = dt
            
            contacts.append(contact)
        
        return contacts

    def clear_stored_contacts(self):
        """Clear the temporary contact storage."""
        print(f"Clearing webform storage: {self.storage_file}")
        self.stored_contacts = []
        self._save_contacts()
    
    def run(self, host: str = '127.0.0.1', port: int = 7173):
        """Run the web form server.
        
        Args:
            host: Host to bind to. Defaults to '127.0.0.1' (localhost only).
                  Use '0.0.0.0' to expose on all network interfaces (security risk).
            port: Port number to listen on.
        """
        if host == '0.0.0.0':
            print("WARNING: Binding to 0.0.0.0 exposes the server to all network interfaces!")
            print("This is a security risk. Only use in controlled environments.")
        print(f"Starting web form server on http://{host}:{port}")
        self.app.run(host=host, port=port, debug=False)


# HTML template for the contact form
CONTACT_FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Contact Submission Form</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .form-container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: bold;
        }
        input, textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 14px;
        }
        textarea {
            resize: vertical;
            min-height: 80px;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
        }
        button:hover {
            background-color: #45a049;
        }
        .message {
            padding: 10px;
            margin-top: 15px;
            border-radius: 4px;
            display: none;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .required {
            color: red;
        }
    </style>
</head>
<body>
    <div class="form-container">
        <h1>Contact Submission Form</h1>
        <form id="contactForm">
            <div class="form-group">
                <label for="first_name">First Name <span class="required">*</span></label>
                <input type="text" id="first_name" name="first_name" required>
            </div>
            <div class="form-group">
                <label for="last_name">Surname <span class="required">*</span></label>
                <input type="text" id="last_name" name="last_name" required>
            </div>
            <div class="form-group">
                <label for="phone">Phone Number <span class="required">*</span></label>
                <input type="tel" id="phone" name="phone" required>
            </div>
            <div class="form-group">
                <label for="suburb">Suburb</label>
                <input type="text" id="suburb" name="suburb">
            </div>
            <div class="form-group">
                <label for="postcode">Postcode</label>
                <input type="text" id="postcode" name="postcode">
            </div>
            
            <!-- Scooter Info -->
            <div class="form-group">
                <label for="scooter_name">Scooter Name</label>
                <input type="text" id="scooter_name" name="scooter_name" placeholder="e.g. My Speedster">
            </div>
            <div class="form-group">
                <label for="scooter_model">Scooter Model</label>
                <input type="text" id="scooter_model" name="scooter_model" placeholder="e.g. Xiaomi Pro 2">
            </div>
            
            <!-- Hidden email for compatibility if needed later -->
            <input type="hidden" name="email" value="">

            <button type="submit">Submit Contact</button>
            <div id="message" class="message"></div>
        </form>
    </div>
    
    <script>
        document.getElementById('contactForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            fetch('/submit', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                const messageDiv = document.getElementById('message');
                messageDiv.textContent = data.message;
                messageDiv.className = 'message success';
                messageDiv.style.display = 'block';
                
                // Reset form
                document.getElementById('contactForm').reset();
                
                // Hide message after 3 seconds
                setTimeout(() => {
                    messageDiv.style.display = 'none';
                }, 3000);
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    </script>
</body>
</html>
"""
