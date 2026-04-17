<?php
// booking.php

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // 1. Capture Form Data
    $customer_name = htmlspecialchars($_POST['name']);
    $customer_email = $_POST['email'];
    
    // Capture vehicle and package from the form, or fallback to 'service'
    $vehicle = isset($_POST['vehicle']) ? $_POST['vehicle'] : '';
    $package = isset($_POST['package']) ? $_POST['package'] : '';
    
    if (!empty($vehicle) && !empty($package)) {
        $service_type = "$vehicle - $package";
    } elseif (isset($_POST['service'])) {
        $service_type = $_POST['service'];
    } else {
        $service_type = "Car Wash Service";
    }

    $booking_date  = $_POST['date'];

    // 2. Email Configuration
    $to = $customer_email;
    $subject = "Car Wash Appointment Confirmed";

    // 3. HTML Message Body
    $message = "
    <html>
    <head>
      <title>Booking Confirmation</title>
      <style>
        body { font-family: Arial, sans-serif; }
        .container { border: 1px solid #ddd; padding: 20px; max-width: 600px; }
        .header { background-color: #007bff; color: white; padding: 10px; }
      </style>
    </head>
    <body>
      <div class='container'>
        <div class='header'>
          <h2>Booking Confirmed!</h2>
        </div>
        <p>Hi $customer_name,</p>
        <p>Your appointment for a <strong>$service_type</strong> has been successfully booked.</p>
        <p><strong>Date:</strong> $booking_date</p>
        <br>
        <p>Thank you for choosing Clean Ride Car Wash.</p>
      </div>
    </body>
    </html>
    ";

    // 4. Headers (Required for HTML & Sender ID)
    // Replace with your actual Gmail address
    $headers  = "MIME-Version: 1.0" . "\r\n";
    $headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
    $headers .= "From: thattilservicecentree@gmail.com" . "\r\n";

    // 5. Send Mail
    if(mail($to, $subject, $message, $headers)) {
        echo "<script>alert('Booking Confirmed! Check your email.'); window.location.href='index.html';</script>";
    } else {
        echo "Error: Email could not be sent. Check server logs.";
    }
}
?>
