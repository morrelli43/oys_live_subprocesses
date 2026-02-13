# Webhook Support and Real-Time Sync

This guide explains how to set up real-time synchronization using webhooks for instant contact updates.

## Overview

The contact sync system supports two methods for detecting changes:

1. **Webhooks (Real-time)** - For Square (native support)
2. **Polling** - For Google Contacts (no native webhook support)

## Webhook Support by Platform

| Platform | Webhook Support | Method |
|----------|----------------|---------|
| **Square** | ✅ Native | Customer webhooks |
| **Google Contacts** | ❌ Not available | Polling with sync tokens |
| **Web Form** | ✅ Native | Direct integration |

## Square Webhooks (Real-Time)

Square provides native webhook support for customer events. When a contact is created, updated, or deleted in Square, your webhook endpoint receives an instant notification.

### Supported Events

- `customer.created` - New customer created
- `customer.updated` - Customer information updated
- `customer.deleted` - Customer deleted
- `customer.merged` - Customer profiles merged

### Setup Instructions

#### 1. Start the Webhook Server

```bash
# Start webhook server on localhost (secure)
python main.py webhook

# Or expose on all interfaces (for production with reverse proxy)
python main.py webhook --host 0.0.0.0 --webhook-port 5001
```

The webhook server will listen on `http://127.0.0.1:5001` by default.

#### 2. Configure Public Endpoint

For Square to reach your webhook, you need a public HTTPS endpoint. Options:

**Development (ngrok):**
```bash
# In another terminal
ngrok http 5001
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

**Production:**
- Use a reverse proxy (nginx, Apache)
- Configure SSL/TLS certificate
- Point to your webhook server

#### 3. Register Webhook in Square Dashboard

1. Go to [Square Developer Dashboard](https://developer.squareup.com/apps)
2. Select your application
3. Navigate to **Webhooks** section
4. Click **Add Subscription**
5. Configure:
   - **Webhook URL**: `https://your-domain.com/webhooks/square`
   - **API Version**: Select latest
   - **Events**: Select `customer.created`, `customer.updated`, etc.
6. Get the **Signature Key** from the dashboard
7. Add to your `.env` file:
   ```
   SQUARE_SIGNATURE_KEY=your_signature_key_here
   ```

#### 4. Test Your Webhook

Create or update a customer in Square:
- Square Point of Sale app
- Square Dashboard
- Square API

Your webhook server will receive the notification and automatically trigger sync.

### How It Works

```
Square Customer Change
        ↓
Square sends webhook POST request
        ↓
Webhook Handler verifies signature
        ↓
Fetch updated contacts from Square
        ↓
Merge into contact store
        ↓
Push to Google Contacts & other sources
        ↓
All systems in sync (instantly!)
```

## Google Contacts (Polling)

Google Contacts API does not support webhooks. Instead, use one of these approaches:

### Option 1: Scheduled Polling (Recommended)

Run sync on a schedule using cron or task scheduler:

```bash
# Every 15 minutes
*/15 * * * * cd /path/to/contact_sync && python main.py sync
```

### Option 2: Sync Tokens (Efficient Polling)

Use Google's sync tokens to fetch only changes since last sync:

```python
from webhook_handler import GoogleContactsPoller

# Initialize poller
poller = GoogleContactsPoller(google_connector, sync_callback=trigger_sync)

# Poll for changes
has_changes = poller.poll_for_changes()
```

Benefits:
- Only fetches changed contacts
- More efficient than full sync
- Reduces API quota usage

### Option 3: Third-Party Services

Use automation platforms that simulate webhooks:
- **Zapier**: Monitor Google Contacts, trigger webhook
- **Make.com**: Watch for contact changes
- **Pipedream**: Poll and forward as webhook

Example Zapier setup:
1. Trigger: Google Contacts - New/Updated Contact
2. Action: Webhooks - POST to `http://your-server/sync-trigger`

## Web Form Integration

The web form supports instant sync since it's part of your system:

```python
# When contact submitted via web form
@app.route('/submit', methods=['POST'])
def submit_contact():
    # Save contact
    save_to_storage(contact_data)
    
    # Trigger immediate sync (optional)
    trigger_sync()  # Push to Google and Square immediately
    
    return jsonify({'status': 'success'})
```

## Architecture for Real-Time Sync

### With Webhooks (Square)

```
┌─────────────┐
│   Square    │ Customer created/updated
└──────┬──────┘
       │ Webhook POST
       ↓
┌─────────────────┐
│ Webhook Handler │ Verify signature
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Sync Engine    │ Fetch, merge, push
└────────┬────────┘
         │
         ↓
┌─────────────────────────────┐
│ Google   │  Web Form  │ ... │ All sources updated
└─────────────────────────────┘
```

### Without Webhooks (Google)

```
┌──────────────┐
│ Cron/Timer   │ Every N minutes
└──────┬───────┘
       │
       ↓
┌─────────────────┐
│  Sync Engine    │ Poll all sources
└────────┬────────┘
         │
         ↓
┌─────────────────────────────┐
│ Google   │  Square    │ ... │ Fetch changes
└────────┬──────────┬─────────┘
         │          │
         └──────┬───┘
                ↓
         ┌──────────────┐
         │ Merge & Push │
         └──────────────┘
```

## Hybrid Approach (Recommended)

Combine both methods for best results:

1. **Webhook for Square** - Instant sync when Square changes
2. **Polling for Google** - Regular sync (e.g., every 15 minutes)
3. **Direct integration for Web Form** - Instant sync on submission

### Implementation

Run both services simultaneously:

```bash
# Terminal 1: Webhook server for Square
python main.py webhook

# Terminal 2: Web form for manual entry
python main.py webform

# Terminal 3 (or cron): Scheduled Google polling
while true; do
    python main.py sync
    sleep 900  # 15 minutes
done
```

Or use a process manager (systemd, supervisor, PM2):

```ini
# /etc/systemd/system/contact-sync-webhook.service
[Unit]
Description=Contact Sync Webhook Server

[Service]
ExecStart=/usr/bin/python3 /path/to/main.py webhook
Restart=always

[Install]
WantedBy=multi-user.target
```

## Security Considerations

### Webhook Security

1. **Signature Verification**: Always verify Square's HMAC signature
2. **HTTPS Only**: Never use HTTP in production
3. **Firewall**: Restrict access to webhook endpoint
4. **Rate Limiting**: Implement rate limiting on webhook endpoint
5. **Timeout**: Respond to webhooks quickly (< 5 seconds)

### Network Security

```bash
# Use localhost for development
python main.py webhook --host 127.0.0.1

# Production: use reverse proxy
# nginx/Apache → webhook server on localhost
# Only reverse proxy exposed to internet
```

## Monitoring and Debugging

### Check Webhook Logs

```bash
# Start webhook server with logs
python main.py webhook

# Watch for incoming webhooks
tail -f webhook.log
```

### Test Webhook Endpoint

```bash
# Health check
curl http://localhost:5001/webhooks/health

# Expected response:
# {"status": "healthy", "timestamp": "2026-02-13T12:00:00"}
```

### Square Webhook Logs

View webhook delivery attempts in Square Dashboard:
- Go to Webhooks section
- Check delivery status (success/failure)
- View payload and response
- Retry failed deliveries

## Performance Considerations

### Webhook Response Time

Webhooks should respond quickly:

```python
# ✅ Good: Acknowledge immediately, process async
@app.route('/webhooks/square', methods=['POST'])
def square_webhook():
    # Verify signature
    verify_signature(request)
    
    # Queue for background processing
    queue.enqueue(process_webhook, request.json)
    
    # Respond immediately
    return jsonify({'status': 'queued'}), 200
```

### Sync Frequency

- **Webhooks**: Instant (< 1 second)
- **Polling (Google)**: Every 15-60 minutes recommended
- **Full sync**: Once per day as backup

## Troubleshooting

### Square Webhook Not Received

1. Check webhook URL is publicly accessible (HTTPS)
2. Verify signature key in `.env` matches Square Dashboard
3. Check firewall/security groups allow Square IPs
4. Review Square webhook logs for delivery failures

### Google Contacts Sync Slow

1. Use sync tokens instead of fetching all contacts
2. Reduce polling frequency if hitting rate limits
3. Implement exponential backoff for API errors

### Webhook Server Crashes

1. Implement error handling in webhook handlers
2. Use process supervisor (systemd, supervisor)
3. Set up monitoring/alerting
4. Log all webhook events for debugging

## Cost and Rate Limits

| Service | Webhooks Cost | Rate Limits |
|---------|---------------|-------------|
| Square | Free | No specific limit on webhook deliveries |
| Google Contacts | N/A (polling) | 10 requests/second, 3000/minute |

## Additional Resources

- [Square Webhooks Documentation](https://developer.squareup.com/docs/webhooks/overview)
- [Square Customer Webhooks](https://developer.squareup.com/docs/customers-api/use-the-api/customer-webhooks)
- [Google People API Sync](https://developers.google.com/people/v1/contacts)
- [ngrok for webhook testing](https://ngrok.com/)

## Summary

✅ **Square**: Use webhooks for instant sync
❌ **Google Contacts**: Use scheduled polling (no webhook support)
✅ **Web Form**: Built-in instant sync

For the best experience, run the webhook server continuously and schedule regular Google polling as a backup.
