# Email Server Configuration Guide

To enable email sending using the `booking.php` script, you must configure your local XAMPP server. Since these files are located in your XAMPP installation directory (outside this project workspace), you need to edit them manually.

## Credentials
- **Email:** `thattilservicecentree@gmail.com`
- **App Password:** `jycr hgbu cyjp bfst`

## Step 1: Configure php.ini

1.  Open `C:\xampp\php\php.ini` in a text editor (Notepad, VS Code, etc.).
2.  Search for `[mail function]`.
3.  Update the settings to match the following:

```ini
[mail function]
SMTP=smtp.gmail.com
smtp_port=587
sendmail_from = thattilservicecentree@gmail.com
sendmail_path = "\"C:\xampp\sendmail\sendmail.exe\" -t"
```

## Step 2: Configure sendmail.ini

1.  Open `C:\xampp\sendmail\sendmail.ini`.
2.  Update the content to match the following (replace existing content or edit specific lines):

```ini
[sendmail]
smtp_server=smtp.gmail.com
smtp_port=587
error_logfile=error.log
debug_logfile=debug.log

; YOUR GMAIL CREDENTIALS
auth_username=thattilservicecentree@gmail.com
auth_password=jycr hgbu cyjp bfst

force_sender=thattilservicecentree@gmail.com
```

## Step 3: Restart Apache

1.  Open the **XAMPP Control Panel**.
2.  Stop **Apache**.
3.  Start **Apache** again to apply changes.

## Step 4: Run

Ensure your web server (Apache) is running and serving the `public` directory. Access the form and submit a booking.
