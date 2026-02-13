"""
Web Form connector for collecting contacts.
"""
from typing import List
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import json
import os

from contact_model import Contact


class WebFormConnector:
    """Simple web form to collect contacts."""
    
    def __init__(self, storage_file: str = 'webform_contacts.json'):
        self.storage_file = storage_file
        self.app = Flask(__name__)
        self._setup_routes()
        self._load_contacts()
    
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
            """Handle contact form submission."""
            data = request.form
            
            contact_data = {
                'first_name': data.get('first_name', ''),
                'last_name': data.get('last_name', ''),
                'email': data.get('email', ''),
                'phone': data.get('phone', ''),
                'company': data.get('company', ''),
                'notes': data.get('notes', ''),
                'timestamp': datetime.now().isoformat()
            }
            
            self.stored_contacts.append(contact_data)
            self._save_contacts()
            
            return jsonify({'status': 'success', 'message': 'Contact submitted successfully!'})
        
        @self.app.route('/api/contacts', methods=['GET'])
        def get_contacts():
            """API endpoint to get all contacts."""
            return jsonify({'contacts': self.stored_contacts})
    
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
            
            # Use timestamp as source ID to ensure uniqueness
            if 'timestamp' in data:
                contact.source_ids['webform'] = data['timestamp']
                contact.last_modified = datetime.fromisoformat(data['timestamp'])
            
            contacts.append(contact)
        
        return contacts
    
    def run(self, host: str = '127.0.0.1', port: int = 5000):
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
                <label for="last_name">Last Name <span class="required">*</span></label>
                <input type="text" id="last_name" name="last_name" required>
            </div>
            <div class="form-group">
                <label for="email">Email <span class="required">*</span></label>
                <input type="email" id="email" name="email" required>
            </div>
            <div class="form-group">
                <label for="phone">Phone</label>
                <input type="tel" id="phone" name="phone">
            </div>
            <div class="form-group">
                <label for="company">Company</label>
                <input type="text" id="company" name="company">
            </div>
            <div class="form-group">
                <label for="notes">Notes</label>
                <textarea id="notes" name="notes"></textarea>
            </div>
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
