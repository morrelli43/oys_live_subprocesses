const nodemailer = require('nodemailer');
require('dotenv').config();

async function sendTestEmail() {
    if (!process.env.SMTP_HOST || !process.env.SMTP_USER || !process.env.SMTP_PASS) {
        console.error('❌ Missing SMTP configuration. Check your .env file.');
        process.exit(1);
    }

    try {
        const transporter = nodemailer.createTransport({
            host: process.env.SMTP_HOST,
            port: process.env.SMTP_PORT || 587,
            secure: process.env.SMTP_SECURE === 'true', // true for 465, false for other ports
            auth: {
                user: process.env.SMTP_USER,
                pass: process.env.SMTP_PASS,
            },
            debug: true, // Enable debug output
            logger: true // Log information to console
        });

        console.log('Attempting to send test email...');
        const info = await transporter.sendMail({
            from: `"Test Script" <${process.env.SMTP_FROM}>`,
            to: 'bookings@onyascoot.com',
            subject: 'Test Email from Debugger',
            text: 'If you receive this, the email sending capability is functioning correctly.',
        });

        console.log('✅ Email sent successfully!');
        console.log('Message ID:', info.messageId);
    } catch (error) {
        console.error('❌ Failed to send email:', error);
    }
}

sendTestEmail();
