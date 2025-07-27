import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.config import config
from src.logger import logger


def send_email(body: str):
    """
    Send an HTML email with a minimalistic, attractive design. The sender name will show as 'Terminator'.
    """
    subject = "You've had a trade! 🤑"
    try:
        # Create message container with correct MIME types
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"Obamanator <{config.EMAIL_FROM}>"
        msg['To'] = config.EMAIL_TO

        # Plain text fallback
        text = f"{subject}\n\n{body}"

        # Minimalistic HTML template
        html = f"""
        <html>
          <head>
            <style>
              body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; margin: 0; padding: 0; }}
              .container {{ width: 100%; max-width: 600px; margin: 20px auto; background: #fff; border-radius: 8px; overflow: hidden; }}
              .header {{ background: #222; color: #fff; padding: 10px 20px; text-align: center; }}
              .content {{ padding: 20px; line-height: 1.5; }}
              .footer {{ background: #f4f4f4; color: #888; font-size: 12px; text-align: center; padding: 10px; }}
              .button {{ display: inline-block; padding: 10px 15px; margin: 10px 0; background: #28a745; color: #fff; text-decoration: none; border-radius: 4px; }}
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h2>{subject}</h2>
              </div>
              <div class="content">
                <p>{body.replace("\n", "<br>")}</p>
              </div>
              <div class="footer">
                <p>Automated Trade Report</p>
              </div>
            </div>
          </body>
        </html>
        """

        # Attach parts
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        msg.attach(part1)
        msg.attach(part2)

        # Send email
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.sendmail(config.EMAIL_FROM, config.EMAIL_TO, msg.as_string())

        logger.info("Email update sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
