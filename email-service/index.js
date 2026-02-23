const express = require('express');
const nodemailer = require('nodemailer');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(express.json());
app.use(cors());

// Health check endpoint
app.get('/health', (req, res) => {
    res.status(200).send('Email Service is running');
});

app.post('/send-email', async (req, res) => {
    const { first_name, surname, number, location, address_line_1, suburb, state, postcode, country, escooter_make, escooter_model, issue, issue_extra, website_url } = req.body;

    // Spam Protection: Honeypot Check
    if (website_url) {
        console.log(`🚫 Spam detected: Honeypot field filled by connection from ${req.ip}`);
        // Return fake success to fool the bot
        return res.status(200).json({ success: true, message: 'Email sent successfully' });
    }

    // Create transporter using Mailu credentials from .env
    const transporter = nodemailer.createTransport({
        host: process.env.SMTP_HOST,
        port: process.env.SMTP_PORT || 587,
        secure: process.env.SMTP_SECURE === 'true', // true for 465, false for other ports
        auth: {
            user: process.env.SMTP_USER,
            pass: process.env.SMTP_PASS,
        },
    });

    const mailOptions = {
        from: `"${first_name} ${surname}" <${process.env.SMTP_FROM}>`,
        to: process.env.EMAIL_RECIPIENT || 'bookings@onyascoot.com',
        subject: `New Booking Enquiry - ${first_name} ${surname}`,
        text: `
New Booking Enquiry Received:

Name: ${first_name} ${surname}
Phone: ${number}
Location: ${location}
Scooter: ${escooter_make} ${escooter_model}
Issue: ${issue}
Extra Details: ${issue_extra || 'None'}

-- 
On Ya Scoot Booking System
        `,
        html: `
            <h3>New Booking Enquiry Received</h3>
            <p><strong>Name:</strong> ${first_name} ${surname}</p>
            <p><strong>Phone:</strong> ${number}</p>
            <p><strong>Location:</strong> ${location}</p>
            <p><strong>Scooter:</strong> ${escooter_make} ${escooter_model}</p>
            <p><strong>Issue:</strong> ${issue}</p>
            <p><strong>Extra Details:</strong> ${issue_extra || 'None'}</p>
            <br>
            <hr>
            <p><small>On Ya Scoot Booking System</small></p>
        `,
    };

    try {
        await transporter.sendMail(mailOptions);
        console.log(`✅ Email sent for ${first_name} ${surname}`);

        // --- Forward to Sync Server (Internal) ---
        // Fire and forget - don't block response
        // Requires 'axios' (ensure it's in package.json)
        const axios = require('axios');

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
            notes: `${issue}: ${issue_extra || ''}`,
            escooter1: `${escooter_make} ${escooter_model}`,
            timestamp: new Date().toISOString()
        };

        // Use Docker service name for internal communication
        const syncUrl = process.env.SYNC_SERVICE_URL || 'http://contact-sync:7173/submit';

        console.log(`Forwarding to sync server: ${syncUrl}`);
        axios.post(syncUrl, syncData)
            .then(() => console.log('✅ Synced to contact-service'))
            .catch(err => console.error('⚠️ Sync failed:', err.message));

        // --- NEW: Forward to Pushbullet (Message Center) ---
        const pushbulletPayload = {
            app: "pushbullet",
            target: "dandroid",
            title: `Submit ${first_name}, ${issue}`,
            body: `Name: ${first_name} ${surname}\nPhone: ${number}\nIssue: ${issue}\n`
        };

        fetch(process.env.PUSH_WEBHOOK_URL || 'https://hooks.morrelli43media.com/webhook/message-center', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(pushbulletPayload)
        })
            .then(response => {
                if (response.ok) {
                    console.log("✅ Alert sent to Message Center successfully.");
                } else {
                    console.error("⚠️ Message Center returned:", response.status);
                }
            })
            .catch(error => console.error("❌ Error sending Message Center alert:", error.message));
        // ----------------------------------------------

        res.status(200).json({ success: true, message: 'Email sent successfully' });
    } catch (error) {
        console.error('❌ SMTP Error:', error);
        res.status(500).json({ success: false, message: 'Failed to send email', error: error.message });
    }
});

const PORT = process.env.PORT || 3002;
app.listen(PORT, () => {
    console.log(`Email service listening on port ${PORT}`);
});
