import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

def send_email(html_content, recipient=None):
    """
    Sends the email using SMTP configuration from .env
    """
    smtp_server = os.getenv("SMTP_SERVER") or "smtp.gmail.com"
    try:
        smtp_port = int(os.getenv("SMTP_PORT") or 587)
    except ValueError:
        smtp_port = 587
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if not recipient:
        recipient = os.getenv("EMAIL_RECIPIENT")
        
    missing_vars = []
    if not smtp_user: missing_vars.append("SMTP_USER")
    if not smtp_password: missing_vars.append("SMTP_PASSWORD")
    if not recipient: missing_vars.append("EMAIL_RECIPIENT")

    if missing_vars:
        print(f"SMTP config missing: {', '.join(missing_vars)}. Skipping email send.")
        # Save to file instead for debugging
        with open("latest_briefing.html", "w") as f:
            f.write(html_content)
        print("Saved to latest_briefing.html")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient
        msg['Subject'] = f"Morning Market Briefing – {datetime.now().strftime('%Y-%m-%d')}"
        
        msg.attach(MIMEText(html_content, 'html'))
        
        if len(recipient) > 4:
            masked_recipient = recipient[:2] + "***" + recipient[recipient.find("@"):]
        else:
            masked_recipient = "***"
        print(f"Sending email to: {masked_recipient}")

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        print(f"Email sent successfully to {masked_recipient}")
        return True
        
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
