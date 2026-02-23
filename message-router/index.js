const express = require('express');
const axios = require('axios');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(express.json());
app.use(cors());

// Health check endpoint
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'ok', service: 'message-router', version: '1.0.0' });
});

/**
 * Main entry point for frontend submissions
 */
app.post('/submit', async (req, res) => {
    const rawData = req.body;

    console.log(`\n[Message Router] Received raw submission: ${rawData.first_name} ${rawData.surname}`);

    const {
        first_name, surname, number, location,
        address_line_1, suburb, state, postcode, country,
        escooter_make, escooter_model, issue, issue_extra
    } = rawData;

    // --- 1. Map to contact-sync ---
    const syncData = {
        first_name: first_name,
        last_name: surname,
        phone: number,
        email: "",
        address_line_1: address_line_1 || "",
        suburb: suburb || "",
        state: state || "",
        postcode: postcode || "",
        country: country || "",
        company: "",
        notes: `${issue || 'No Issue'}: ${issue_extra || ''}`,
        escooter1: `${escooter_make || ''} ${escooter_model || ''}`.trim(),
        timestamp: new Date().toISOString()
    };

    // --- 2. Map to node-box (Alerts) ---
    const alertPayload = {
        app: "pushbullet",
        target: "dandroid",
        title: `Submit ${first_name}, ${issue || 'New Lead'}`,
        body: `Name: ${first_name} ${surname}\nPhone: ${number}\nIssue: ${issue || 'No Issue'}\n`
    };

    // Define service URLs
    const contactSyncUrl = process.env.CONTACT_SYNC_URL || 'http://contact-sync:7173/submit';
    const emailServiceUrl = process.env.EMAIL_SERVICE_URL || 'http://email-service:3002/send-email';
    const nodeBoxUrl = process.env.NODE_BOX_URL || 'http://node-box:3003/push';

    // Fan out requests in background
    console.log(`[Message Router] Routing to sub-processes...`);

    // We respond success immediately to the frontend, but wait for downstream to trigger in background
    // for robust logging and potential retry logic in the future.

    // 1. Sync to Contacts
    axios.post(contactSyncUrl, syncData)
        .then(() => console.log('✅ Routed to Contact-Sync'))
        .catch(err => console.error('⚠️ Contact-Sync routing failed:', err.message));

    // 2. Trigger Node-Box (Alerts)
    axios.post(nodeBoxUrl, alertPayload)
        .then(() => console.log('✅ Routed to Node-Box'))
        .catch(err => console.error('⚠️ Node-Box routing failed:', err.message));

    // 3. Trigger Email-Service
    axios.post(emailServiceUrl, rawData)
        .then(() => console.log('✅ Routed to Email-Service'))
        .catch(err => console.error('⚠️ Email-Service routing failed:', err.message));

    res.status(200).json({
        success: true,
        message: 'Submission received and routing in progress'
    });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
    console.log(`Message Router listening on port ${PORT}`);
    console.log(`Contact-Sync: ${process.env.CONTACT_SYNC_URL || 'http://contact-sync:7173/submit'}`);
    console.log(`Email-Service: ${process.env.EMAIL_SERVICE_URL || 'http://email-service:3002/send-email'}`);
    console.log(`Node-Box: ${process.env.NODE_BOX_URL || 'http://node-box:3003/push'}`);
});
