"""
Webhook and Webform listener for V2 architecture.
Combines all POST endpoints into a single memory-first Flask app.
"""
from flask import Flask, request, jsonify
import hmac
import hashlib
import os

class WebhookServer:
    def __init__(self, sync_engine, port=7173):
        self.app = Flask(__name__)
        self.port = port
        self.engine = sync_engine
        
        # Square config
        self.square_signature_key = os.getenv('SQUARE_SIGNATURE_KEY')
        self.square_webhook_url = os.getenv('SQUARE_WEBHOOK_URL')

        # Register Routes
        self.app.route('/health', methods=['GET'])(self.health_check)
        self.app.route('/submit', methods=['POST', 'OPTIONS'])(self.handle_webform)
        self.app.route('/webhooks/square', methods=['POST'])(self.handle_square)

    def health_check(self):
        return jsonify({"status": "ok", "version": "v2.0"}), 200

    def handle_webform(self):
        """Immediately parse and drop webforms into the sync engine memory."""
        if request.method == 'OPTIONS':
            return '', 204

        try:
            # Handle JSON or Form-Data
            if request.is_json:
                data = request.json
            else:
                data = request.form.to_dict()

            print(f"\n[WebhookServer] Received /submit payload: {data.get('email')} / {data.get('phone')}")
            
            # Immediately hand off to engine for memory parsing and instapush
            success = self.engine.process_incoming_webhook(data, source_name='webform')
            
            if success:
                return jsonify({"status": "success", "message": "Contact pushed instantly."}), 200
            else:
                return jsonify({"status": "error", "message": "Missing usable phone number"}), 400

        except Exception as e:
            print(f"[WebhookServer] Error processing /submit: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    def handle_square(self):
        """Process real-time Square customer events."""
        print("\n[WebhookServer] Received Square Event")
        signature = request.headers.get('x-square-hmacsha256-signature')
        
        if self.square_signature_key and self.square_webhook_url:
            if not signature or not self._verify_square_signature(request.get_data(), signature):
                print("  Invalid Square signature")
                return jsonify({'error': 'Unauthorized'}), 401
                
        # For Square webhooks, we actually just trigger a global sync
        # Since Square is the source of truth, pulling the fresh data from Square
        # and forcefully distributing it outward is safest.
        payload = request.json
        if not payload:
            return jsonify({'error': 'Invalid payload'}), 400
            
        event_type = payload.get('type')
        if event_type in ['customer.created', 'customer.updated']:
            print(f"  Square Event: {event_type} - Syncing all...")
            # Fire sync in background thread to not block webhook response
            import threading
            threading.Thread(target=self.engine.sync_all).start()
        elif event_type == 'customer.deleted':
            # Extract the deleted customer ID and propagate deletion
            customer_id = (payload.get('data', {}).get('object', {}).get('customer', {}).get('id') or
                           payload.get('data', {}).get('id'))
            if customer_id:
                print(f"  Square Event: customer.deleted - Customer ID: {customer_id}")
                import threading
                threading.Thread(target=self.engine.handle_square_deletion, args=(customer_id,)).start()
            else:
                print("  Square Event: customer.deleted - Could not extract customer ID")
            
        return jsonify({'status': 'received'}), 200

    def _verify_square_signature(self, body, signature):
        body_str = body.decode('utf-8')
        sig_string = self.square_webhook_url + body_str
        
        hmac_obj = hmac.new(
            self.square_signature_key.encode('utf-8'),
            sig_string.encode('utf-8'),
            hashlib.sha256
        )
        
        computed_signature = hmac_obj.digest()
        import base64
        computed_b64 = base64.b64encode(computed_signature).decode('utf-8')
        
        return hmac.compare_digest(computed_b64, signature)

    def run(self, host='0.0.0.0'):
        print(f"\n[WebhookServer] Starting V2 combined listener on {host}:{self.port}")
        self.app.run(host=host, port=self.port, debug=False)
