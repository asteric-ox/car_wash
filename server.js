require('dotenv').config();
const express = require('express');
const mysql = require('mysql2');
const bodyParser = require('body-parser');
const nodemailer = require('nodemailer');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

// Database Connection
const db = mysql.createPool({
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'carwash_db'
});

// Check DB Connection (Async)
db.getConnection((err, connection) => {
    if (err) {
        console.error('Database connection failed:', err.code);
        console.log('Continuing without database... (Mock Mode)');
    } else {
        console.log('Connected to MySQL Database');
        connection.release();
    }
});

// Routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Mock Weather Endpoint
app.get('/api/weather', (req, res) => {
    // In a real app, fetch from OpenWeatherMap
    const forecasts = [
        { desc: "Sunny skies ahead—Perfect day for a wash!", icon: "☀️" },
        { desc: "Rain expected tomorrow—Book a rain-check wax today!", icon: "🌧️" },
        { desc: "Perfect weather for a ceramic coating!", icon: "✨" }
    ];
    const random = forecasts[Math.floor(Math.random() * forecasts.length)];
    res.json(random);
});

// Booking Endpoint
app.post('/api/book', (req, res) => {
    const { name, email, phone, vehicleType, package: servicePackage, date, time, addons } = req.body;

    // 1. Insert into Database
    const sql = `INSERT INTO bookings (customer_name, email, phone, vehicle_type, service_package, appointment_date, appointment_time, addons) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;
    const addonsString = addons ? addons.join(', ') : '';

    // Note: In production, handle DB errors properly.
    db.query(sql, [name, email, phone, vehicleType, servicePackage, date, time, addonsString], (err, result) => {
        if (err) {
            console.error('Error saving booking:', err);
            // We might still want to try sending email or return error
            // For now, let's assume success if DB fails (demo mode) or return error
            // return res.status(500).json({ success: false, message: 'Database error' });
        }

        const bookingId = result ? result.insertId : Math.floor(Math.random() * 10000);

        // 2. Send Email
        sendConfirmationEmail(bookingId, { name, email, vehicleType, servicePackage, date, time, addonsString }, res);
    });
});

function sendConfirmationEmail(bookingId, details, res) {
    const transporter = nodemailer.createTransport({
        service: process.env.EMAIL_SERVICE || 'gmail',
        auth: {
            user: process.env.EMAIL_USER,
            pass: process.env.EMAIL_PASS
        }
    });

    const mailOptions = {
        from: process.env.EMAIL_USER,
        to: details.email,
        subject: `Your Car Wash is Confirmed! 🧼 [Appointment ID: #${bookingId}]`,
        html: `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
                <h2 style="color: #007bff;">Your Car Wash is Confirmed! 🧼</h2>
                <p>Hi <strong>${details.name}</strong>,</p>
                <p>Get ready to shine! Your appointment at <strong>ProWash Service</strong> is confirmed.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 5px solid #007bff;">
                    <p><strong>Service:</strong> ${details.servicePackage} (${details.vehicleType})</p>
                    <p><strong>Add-ons:</strong> ${details.addonsString || 'None'}</p>
                    <p><strong>Date:</strong> ${details.date}</p>
                    <p><strong>Time:</strong> ${details.time}</p>
                </div>

                <p>Please arrive 5 minutes early. If you need to reschedule, please contact us.</p>
                <p>See you soon!<br><strong>The ProWash Service Team</strong></p>
            </div>
        `
    };

    // If no email creds, just log it
    if (!process.env.EMAIL_USER) {
        console.log('Email not configured. Mocking success.');
        return res.json({ success: true, message: 'Booking confirmed (Email mocked)', bookingId });
    }

    transporter.sendMail(mailOptions, (error, info) => {
        if (error) {
            console.log('Error sending email:', error);
            return res.status(500).json({ success: false, message: 'Email failed' });
        } else {
            console.log('Email sent: ' + info.response);
            res.json({ success: true, message: 'Booking confirmed', bookingId });
        }
    });
}

// Loyalty Check (Mock)
app.get('/api/loyalty/:phone', (req, res) => {
    // In real app, query DB count of completed bookings
    const count = Math.floor(Math.random() * 6); // 0 to 5
    res.json({ stamps: count, freeWash: count >= 5 });
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
