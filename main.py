"""
Main application for contact synchronization.
"""
import argparse
import os
import sys
import time
import threading
from datetime import datetime, timezone
from dotenv import load_dotenv

from contact_model import ContactStore
from sync_engine import SyncEngine
from google_connector import GoogleContactsConnector
from square_connector import SquareConnector
from webform_connector import WebFormConnector
from webhook_handler import WebhookHandler


VERSION = "1.0.1"


def setup_connectors(engine: SyncEngine, config: dict):
    """Setup and register all connectors based on configuration."""
    
    # Google Contacts
    if config.get('enable_google', False):
        try:
            print("Setting up Google Contacts connector...")
            google = GoogleContactsConnector(
                credentials_file=config.get('google_credentials', 'credentials.json'),
                token_file=config.get('google_token', 'token.json')
            )
            engine.register_connector('google', google)
            print("  Google Contacts connector registered")
        except Exception as e:
            print(f"  Warning: Could not setup Google connector: {e}")
    
    # Square
    if config.get('enable_square', False):
        try:
            print("Setting up Square connector...")
            square = SquareConnector(access_token=config.get('square_access_token'))
            engine.register_connector('square', square)
            print("  Square connector registered")
        except Exception as e:
            print(f"  Warning: Could not setup Square connector: {e}")
    
    # Web Form
    if config.get('enable_webform', False):
        try:
            print("Setting up Web Form connector...")
            webform = WebFormConnector(
                storage_file=config.get('webform_storage', 'webform_contacts.json')
            )
            engine.register_connector('webform', webform)
            print("  Web Form connector registered")
        except Exception as e:
            print(f"  Warning: Could not setup Web Form connector: {e}")


def load_config() -> dict:
    """Load configuration from environment variables."""
    load_dotenv()
    
    return {
        'enable_google': os.getenv('ENABLE_GOOGLE', 'false').lower() == 'true',
        'google_credentials': os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json'),
        'google_token': os.getenv('GOOGLE_TOKEN_FILE', 'token.json'),
        
        'enable_square': os.getenv('ENABLE_SQUARE', 'false').lower() == 'true',
        'square_access_token': os.getenv('SQUARE_ACCESS_TOKEN'),
        
        'enable_webform': os.getenv('ENABLE_WEBFORM', 'true').lower() == 'true',
        'webform_storage': os.getenv('WEBFORM_STORAGE', 'webform_contacts.json'),
    }


def main():
    """Main application entry point."""
    print(f"Starting Contact Sync Service v{VERSION}")
    
    parser = argparse.ArgumentParser(
        description=f'Contact Sync v{VERSION} - Synchronize contacts across Google, Square, and Web Form'
    )
    
    parser.add_argument(
        'command',
        choices=['sync', 'stats', 'export', 'import', 'webform', 'webhook', 'serve'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=1800,
        help='Sync interval in seconds for serve command (default: 1800)'
    )
    
    parser.add_argument(
        '--file',
        help='File for import/export operations'
    )

    parser.add_argument(
        '--format',
        choices=['json', 'vcard'],
        default='json',
        help='Format for export (default: json)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=7173,
        help='Port for web form server (default: 7173)'
    )
    
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host for web form server (default: 127.0.0.1). Use 0.0.0.0 to expose on all interfaces.'
    )
    
    parser.add_argument(
        '--webhook-port',
        type=int,
        default=5001,
        help='Port for webhook server (default: 5001)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Initialize store and engine
    store = ContactStore()
    engine = SyncEngine(store)
    
    # Setup connectors
    setup_connectors(engine, config)
    
    # Execute command
    if args.command == 'sync':
        print("\n" + "=" * 60)
        print("CONTACT SYNCHRONIZATION")
        print("=" * 60 + "\n")
        
        if not engine.connectors:
            print("ERROR: No connectors enabled!")
            print("Please configure at least one connector in .env file")
            print("See README.md for configuration instructions")
            sys.exit(1)
        
        success = engine.sync_all()
        
        if success:
            print("\n✓ Synchronization completed successfully")
        else:
            print("\n✗ Synchronization completed with errors")
        
        # Display stats
        stats = engine.get_sync_stats()
        print(f"\nTotal unique contacts: {stats['total_contacts']}")
        for source, count in stats['sources'].items():
            print(f"  {source}: {count} contacts")
    
    elif args.command == 'stats':
        stats = engine.get_sync_stats()
        print("\nContact Statistics:")
        print(f"Total unique contacts: {stats['total_contacts']}")
        print("\nContacts by source:")
        for source, count in stats['sources'].items():
            print(f"  {source}: {count} contacts")
        print("\nLast sync times:")
        for source, time in stats['last_sync_times'].items():
            print(f"  {source}: {time or 'Never'}")
    
    elif args.command == 'export':
        filename = args.file
        if not filename:
            filename = 'contacts.vcf' if args.format == 'vcard' else 'contacts_export.json'
            
        # First sync to get latest data
        if engine.connectors:
            source_contacts = engine.fetch_all_contacts()
            engine.merge_contacts(source_contacts)
        
        if args.format == 'vcard':
            contacts = engine.store.get_all_contacts()
            with open(filename, 'w') as f:
                for contact in contacts:
                    f.write(contact.to_vcard())
                    f.write('\n')
            print(f"Exported {len(contacts)} contacts to {filename} in vCard format.")
        else:
            engine.export_contacts(filename)
            print(f"Exported contacts to {filename} in JSON format.")
    
    elif args.command == 'import':
        if not args.file:
            print("ERROR: --file parameter required for import")
            sys.exit(1)
        engine.import_contacts(args.file)
        print("Import completed. Run 'sync' to push to all sources.")
    
    elif args.command == 'webform':
        print("\nStarting web form server...")
        print("Note: This is a standalone server for contact submission")
        print("Use 'sync' command separately to synchronize collected contacts")
        
        if 'webform' not in engine.connectors:
            print("\nERROR: Web form connector not enabled")
            print("Set ENABLE_WEBFORM=true in .env file")
            sys.exit(1)
        
        webform = engine.connectors['webform']
        webform.engine = engine
        webform.run(host=args.host, port=args.port)
    
    elif args.command == 'serve':
        print("\n" + "=" * 60)
        print("STARTING UNIFIED SYNC SERVER")
        print("=" * 60 + "\n")
        
        # 1. Start periodic sync thread
        def periodic_sync():
            print(f"Periodic sync thread started (Interval: {args.interval}s)")
            while True:
                time.sleep(args.interval)
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Triggering periodic sync...")
                engine.sync_all()
        
        threading.Thread(target=periodic_sync, daemon=True).start()
        
        # 2. Start Webhook server (in thread)
        if config.get('enable_square', False):
            webhook_handler = WebhookHandler(engine, store)
            threading.Thread(target=webhook_handler.run, kwargs={'host': args.host, 'port': args.webhook_port}, daemon=True).start()
        
        # 3. Start Webform server (main thread)
        if 'webform' not in engine.connectors:
            print("\nERROR: Web form connector not enabled. Refusing to start.")
            sys.exit(1)
            
        webform = engine.connectors['webform']
        webform.engine = engine
        webform.run(host=args.host, port=args.port)

    elif args.command == 'webhook':
        print("\nStarting webhook server for real-time sync...")
        print("This server listens for webhook notifications from Square and other sources")
        print("Configure webhook URLs in Square Developer Dashboard:")
        print(f"  Square webhook URL: http://{args.host}:{args.webhook_port}/webhooks/square")
        
        webhook_handler = WebhookHandler(engine, store)
        webhook_handler.run(host=args.host, port=args.webhook_port)


if __name__ == '__main__':
    main()
