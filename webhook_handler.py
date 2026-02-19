"""
Webhook handler for real-time contact sync notifications.

This module provides webhook endpoints to receive instant notifications when
contacts are created or updated in Square. For Google Contacts, which doesn't
support webhooks, we use polling with sync tokens.
"""
from flask import Flask, request, jsonify
import base64
import hashlib
import hmac
import os
from typing import Callable, Optional
from datetime import datetime

from contact_model import ContactStore
from sync_engine import SyncEngine


class WebhookHandler:
    """Handles webhook notifications from various sources."""
    
    def __init__(self, engine: SyncEngine, store: ContactStore, app=None):
        self.app = app or Flask(__name__)
        self.engine = engine
        self.store = store
        self.square_signature_key = os.getenv('SQUARE_SIGNATURE_KEY')
        self.square_webhook_url = os.getenv('SQUARE_WEBHOOK_URL', '')
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes for webhook endpoints."""
        
        @self.app.route('/webhooks/square', methods=['POST'])
        def square_webhook():
            """Handle Square customer webhook notifications."""
            # Verify webhook signature
            if not self._verify_square_signature(request):
                return jsonify({'error': 'Invalid signature'}), 401
            
            data = request.json
            event_type = data.get('type')
            
            # Handle different customer events
            if event_type in ['customer.created', 'customer.updated', 'customer.merged']:
                print(f"Received Square webhook: {event_type}")
                
                # Trigger sync for Square connector
                self._handle_square_event(data)
                
                return jsonify({'status': 'success'}), 200
            
            return jsonify({'status': 'ignored'}), 200
        
        @self.app.route('/webhooks/google', methods=['POST'])
        def google_webhook():
            """
            Placeholder for Google webhook handler.
            
            Note: Google Contacts API does not natively support webhooks.
            Use polling with sync tokens instead via the google_connector.
            """
            return jsonify({
                'status': 'not_supported',
                'message': 'Google Contacts API does not support webhooks. Use polling.'
            }), 501
        
        @self.app.route('/webhooks/health', methods=['GET'])
        def health_check():
            """Health check endpoint for webhook server."""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat()
            }), 200
    
    def _verify_square_signature(self, request) -> bool:
        """
        Verify Square webhook signature.
        
        Square sends a signature in the x-square-hmacsha256-signature header.
        We must verify this to ensure the webhook is authentic.
        """
        if not self.square_signature_key:
            print("Warning: SQUARE_SIGNATURE_KEY not configured, skipping verification")
            return True  # In dev mode, allow without verification
        
        signature = request.headers.get('x-square-hmacsha256-signature')
        if not signature:
            print("No signature header found")
            return False
        
        # Compute expected signature
        # Use the configured public URL (what Square signs against)
        # rather than the internal proxy URL from request.url
        webhook_url = self.square_webhook_url or request.url
        body = request.get_data()
        
        # Square signature = Base64(HMAC-SHA256(signature_key, url + body))
        payload = webhook_url.encode() + body
        expected_signature = base64.b64encode(
            hmac.new(
                self.square_signature_key.encode(),
                payload,
                hashlib.sha256
            ).digest()
        ).decode()
        
        # Compare signatures (constant-time comparison)
        return hmac.compare_digest(signature, expected_signature)
    
    def _handle_square_event(self, event_data: dict):
        """
        Handle Square customer event by triggering selective sync.
        
        Instead of syncing all contacts, we could fetch just the updated
        customer and merge it. For simplicity, this triggers a full sync.
        """
        try:
            # Extract event details
            event_type = event_data.get('type')
            entity_id = event_data.get('data', {}).get('id')
            
            print(f"Processing Square event: {event_type} for entity {entity_id}")
            
            # Trigger sync (in production, use a task queue)
            if 'square' in self.engine.connectors:
                # Fetch from Square
                square_connector = self.engine.connectors['square']
                contacts = square_connector.fetch_contacts()
                
                # Merge into store
                for contact in contacts:
                    self.store.add_contact(contact)
                
                # Push to other sources
                all_contacts = self.store.get_all_contacts()
                self.engine.push_to_all_sources(all_contacts)
                
                print(f"Sync triggered by webhook completed successfully")
        
        except Exception as e:
            print(f"Error handling Square webhook event: {e}")
    
    def run(self, host: str = '127.0.0.1', port: int = 5001):
        """
        Run the webhook server.
        
        Args:
            host: Host to bind to (default: localhost for security)
            port: Port to listen on (default: 5001)
        """
        if host == '0.0.0.0':
            print("WARNING: Binding to 0.0.0.0 exposes webhook server to all network interfaces!")
            print("Ensure proper security measures are in place (firewall, reverse proxy, etc.)")
        
        print(f"Starting webhook server on http://{host}:{port}")
        print("Webhook endpoints:")
        print(f"  - POST http://{host}:{port}/webhooks/square  (Square customer events)")
        print(f"  - GET  http://{host}:{port}/webhooks/health  (health check)")
        
        self.app.run(host=host, port=port, debug=False)


class GoogleContactsPoller:
    """
    Polling-based change detection for Google Contacts.
    
    Since Google Contacts API doesn't support webhooks, we use sync tokens
    to efficiently poll for changes without downloading all contacts.
    """
    
    def __init__(self, google_connector, sync_callback: Optional[Callable] = None):
        """
        Initialize poller.
        
        Args:
            google_connector: GoogleContactsConnector instance
            sync_callback: Function to call when changes are detected
        """
        self.google_connector = google_connector
        self.sync_callback = sync_callback
        self.sync_token = None
    
    def poll_for_changes(self) -> bool:
        """
        Poll Google Contacts for changes using sync tokens.
        
        Returns:
            True if changes were detected, False otherwise
        """
        try:
            # Note: This is a placeholder for sync token implementation
            # The actual implementation would use the People API's syncToken
            # to fetch only changed contacts
            
            print("Polling Google Contacts for changes...")
            
            # In a real implementation:
            # 1. Use connections.list with syncToken parameter
            # 2. Get updated/deleted contacts since last sync
            # 3. Trigger callback if changes found
            
            # For now, fetch all contacts (simplified)
            contacts = self.google_connector.fetch_contacts()
            
            if contacts and self.sync_callback:
                self.sync_callback(contacts)
                return True
            
            return False
        
        except Exception as e:
            print(f"Error polling Google Contacts: {e}")
            return False
