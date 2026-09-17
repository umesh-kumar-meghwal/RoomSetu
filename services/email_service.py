
import os
import logging
import smtplib

from email.message import EmailMessage
from dotenv import load_dotenv


# Load .env file
load_dotenv()


# Logging setup
logger = logging.getLogger(__name__)


class EmailService:

    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        body: str
    ) -> bool:
        print("========== EMAIL FUNCTION CALLED ==========")
        print("TO EMAIL:", to_email)
        print("SUBJECT:", subject)

        try:
            # SMTP configuration
            mail_server = os.getenv(
                "MAIL_SERVER",
                "smtp.gmail.com"
            )

            mail_port = int(
                os.getenv("MAIL_PORT", "587")
            )

            mail_user = os.getenv(
                "MAIL_USERNAME"
            )

            mail_password = os.getenv(
                "MAIL_PASSWORD"
            )

            mail_sender = os.getenv(
                "MAIL_DEFAULT_SENDER",
                mail_user
            )

            # Validate credentials
            if not mail_user:
                raise ValueError(
                    "MAIL_USERNAME is missing in .env"
                )

            if not mail_password:
                raise ValueError(
                    "MAIL_PASSWORD is missing in .env"
                )

            if not to_email:
                raise ValueError(
                    "Recipient email is missing"
                )

            # Create email
            message = EmailMessage()

            message["From"] = mail_sender
            message["To"] = to_email
            message["Subject"] = subject

            message.set_content(body)

            # Connect to SMTP server
            with smtplib.SMTP(
                mail_server,
                mail_port,
                timeout=30
            ) as server:

                # Enable TLS encryption
                server.ehlo()
                server.starttls()
                server.ehlo()

                # Login to Gmail
                server.login(
                    mail_user,
                    mail_password
                )

                # Send email
                server.sendmail(
                    mail_user,
                    [to_email],
                    message.as_string()
                )

            logger.info(
                "Email sent successfully to %s",
                to_email
            )

            print(
                f"EMAIL SENT SUCCESSFULLY: {to_email}"
            )

            return True

        except Exception as exc:

            logger.exception(
                "Failed to send email to %s",
                to_email
            )

            print(
                f"EMAIL ERROR: {exc}"
            )

            return False