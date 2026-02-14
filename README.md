# Contact Sync

A contact synchronization system that connects Google Contacts, Square Up, and a custom web form to create a unified contact list across all platforms.

## Features

- **Multi-Source Sync**: Collect contacts from Google Contacts, Square Up, and a custom web form
- **Smart Merging**: Automatically merge duplicate contacts while preserving all information
- **Bidirectional Sync**: Push updates back to Google Contacts and Square Up
- **Change Detection**: When a contact is updated in one source, the change propagates to others
- **Real-Time Webhooks**: Instant sync when Square contacts change (see [WEBHOOKS.md](WEBHOOKS.md))
- **Web Form**: Simple web interface for collecting new contacts

## Architecture

The system consists of several components:

1. **Contact Model** (`contact_model.py`): Core data structures for contacts with merge capabilities
2. **Connectors**: Individual connectors for each contact source
   - Google Contacts (`google_connector.py`)
   - Square Up (`square_connector.py`)
   - Web Form (`webform_connector.py`)
3. **Sync Engine** (`sync_engine.py`): Orchestrates synchronization across all sources
4. **Webhook Handler** (`webhook_handler.py`): Receives real-time notifications from Square
5. **Main Application** (`main.py`): CLI interface for running sync operations

## Installation

1. Clone the repository:
```bash
git clone https://github.com/morrelli43/contact_sync.git
cd contact_sync
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the application (see Configuration section below)

## Configuration

### 1. Copy the example configuration:
```bash
cp .env.example .env
```

### 2. Configure Google Contacts (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the People API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials as `credentials.json` in the project directory
6. Set `ENABLE_GOOGLE=true` in `.env`

### 3. Configure Square Up (Optional)

1. Go to [Square Developer Dashboard](https://developer.squareup.com/)
2. Create an application or select an existing one
3. Get your access token (use sandbox token for testing)
4. Add your token to `.env`:
```
ENABLE_SQUARE=true
SQUARE_ACCESS_TOKEN=your_token_here
```

### 4. Configure Web Form (Enabled by default)

The web form is enabled by default and requires no additional configuration. Contacts are stored in `webform_contacts.json`.

## Docker

Build the image:
```bash
docker build -t contact-sync .
```

Run sync using your `.env` file (mounting the project directory keeps data files like `webform_contacts.json`):
```bash
docker run --env-file .env -v $(pwd):/app contact-sync sync
```

Example `docker-compose.yml`:
```yaml
services:
  contact-sync:
    build: .
    command: ["sync"]
    env_file: .env
    volumes:
      - ./:/app
    ports:
      - "5000:5000"   # webform
      - "5001:5001"   # webhook
```

For web servers, expose all interfaces inside the container:
- Web form: `docker compose run --service-ports contact-sync webform --host 0.0.0.0 --port 5000`
- Webhook server: `docker compose run --service-ports contact-sync webhook --host 0.0.0.0 --webhook-port 5001`

## Usage

### Synchronize Contacts

Run a full synchronization cycle:
```bash
python main.py sync
```

This will:
1. Fetch contacts from all enabled sources
2. Merge duplicate contacts intelligently
3. Push merged contacts back to Google and Square
4. Save sync state for tracking

### View Statistics

Display contact statistics:
```bash
python main.py stats
```

### Export Contacts

Export all contacts to JSON:
```bash
python main.py export --file contacts_backup.json
```

### Import Contacts

Import contacts from JSON:
```bash
python main.py import --file contacts_backup.json
```

### Run Web Form Server

Start the web form for collecting contacts:
```bash
python main.py webform --port 5000
```

Access the form at `http://localhost:5000`

### Start Webhook Server (Real-Time Sync)

For instant synchronization when Square contacts change:
```bash
python main.py webhook --webhook-port 5001
```

Configure the webhook URL in Square Dashboard. See [WEBHOOKS.md](WEBHOOKS.md) for detailed setup instructions.

## Sync Methods

The system supports two synchronization methods:

1. **Scheduled/Manual Sync** (All sources)
   ```bash
   python main.py sync
   ```
   Run manually or schedule with cron for periodic synchronization.

2. **Real-Time Webhooks** (Square only)
   ```bash
   python main.py webhook
   ```
   Receives instant notifications when Square contacts change. Google Contacts doesn't support webhooks, so use scheduled sync for Google.

**📖 For webhook setup and real-time sync, see [WEBHOOKS.md](WEBHOOKS.md)**

## How It Works

### Contact Merging

Contacts are merged based on email addresses. When two contacts share the same email:
- All non-empty fields are preserved
- Multiple addresses are combined
- Source IDs are maintained for all sources
- Notes are concatenated

### Synchronization Flow

1. **Fetch**: Retrieve contacts from all configured sources
2. **Merge**: Combine contacts using intelligent deduplication
3. **Push**: Update all sources with the merged contact list
4. **Track**: Save sync state and timestamps

### Change Propagation

When a contact is updated in one source:
1. The sync process detects the change based on modification time
2. The updated contact is merged with existing data
3. The merged contact is pushed to all other sources
4. All sources maintain a consistent view

## File Structure

```
contact_sync/
├── main.py                  # CLI application
├── contact_model.py         # Contact data structures
├── sync_engine.py          # Synchronization logic
├── google_connector.py     # Google Contacts API
├── square_connector.py     # Square Up API
├── webform_connector.py    # Web form server
├── requirements.txt        # Python dependencies
├── .env.example           # Configuration template
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## Running Automated Sync

To run sync automatically, set up a cron job (Linux/Mac) or Task Scheduler (Windows):

### Cron Example (every hour):
```bash
0 * * * * cd /path/to/contact_sync && python main.py sync
```

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- Store API credentials securely
- Use environment-specific access tokens (sandbox vs. production)
- The `credentials.json` and `token.json` files contain sensitive data

## Troubleshooting

### Google Authentication Issues
- Ensure `credentials.json` is in the project directory
- Delete `token.json` to re-authenticate
- Check that the People API is enabled in Google Cloud Console

### Square API Issues
- Verify your access token is correct
- Check if you're using the right environment (sandbox vs. production)
- Ensure your Square account has the Customers API enabled

### Missing Contacts
- Run `python main.py stats` to see contact counts per source
- Check sync state in `sync_state.json`
- Review logs for any error messages

## Development

To contribute or modify the system:

1. Follow the modular architecture
2. Each connector should implement `fetch_contacts()` and optionally `push_contact()`
3. Add new connectors by creating a similar class structure
4. Register new connectors in `main.py`

## License

This project is open source. See LICENSE file for details.

## Support

For issues or questions, please open an issue on GitHub.
