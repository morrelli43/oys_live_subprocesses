# Quick Start Guide

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Basic Configuration

1. Copy the example configuration:
```bash
cp .env.example .env
```

2. Edit `.env` to enable the sources you want to use:
```bash
# For Google Contacts
ENABLE_GOOGLE=true
# Download credentials.json from Google Cloud Console

# For Square
ENABLE_SQUARE=true
SQUARE_ACCESS_TOKEN=your_token_here

# For Web Form (enabled by default)
ENABLE_WEBFORM=true
```

## Usage Examples

### Run a Full Sync
```bash
python main.py sync
```
This will:
- Fetch contacts from all enabled sources
- Merge duplicates intelligently
- Push updates back to Google and Square

### View Statistics
```bash
python main.py stats
```

### Export All Contacts
```bash
python main.py export --file backup.json
```

### Import Contacts
```bash
python main.py import --file backup.json
python main.py sync  # Push imported contacts to sources
```

### Start Web Form Server
```bash
# Localhost only (secure)
python main.py webform

# Accessible from network (use with caution)
python main.py webform --host 0.0.0.0 --port 8080
```

## Try the Demo

Run the demo without any API configuration:
```bash
python demo.py
```

This demonstrates the sync process with mock data.

## Automated Sync

Set up a cron job to sync every hour:
```bash
0 * * * * cd /path/to/contact_sync && /usr/bin/python3 main.py sync >> sync.log 2>&1
```

## Troubleshooting

### "No connectors enabled"
- Check your `.env` file
- Ensure at least one source is enabled (ENABLE_GOOGLE=true, etc.)

### Google authentication issues
- Delete `token.json` and re-authenticate
- Ensure `credentials.json` is in the project directory

### Square API errors
- Verify your access token is correct
- Check if you're using sandbox vs production environment

## Security Notes

- Never commit `.env`, `credentials.json`, or `token.json`
- The web form defaults to localhost (127.0.0.1) for security
- Use environment-specific tokens (sandbox for testing)
