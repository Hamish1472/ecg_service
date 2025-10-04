import os
import mimetypes
import smtplib
from email.message import EmailMessage
from ecg_service.config import EMAIL_SENDER, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT

MAX_ATTACHMENT_SIZE_MB = 25
MAX_ATTACHMENT_SIZE = MAX_ATTACHMENT_SIZE_MB * 1024 * 1024  # bytes


def send_email(recipient: str, subject: str, body: str, attachment_path: str = None):
    """
    Sends an email with optional attachment.

    Args:
        recipient (str): Email recipient.
        subject (str): Email subject line.
        body (str): Email body text.
        attachment_path (str, optional): Path to attachment file.
    """
    msg = EmailMessage()
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    if attachment_path:
        attachment_size = os.path.getsize(attachment_path)
        if attachment_size > MAX_ATTACHMENT_SIZE:
            raise ValueError(
                f"Attachment too large ({attachment_size / (1024 * 1024):.2f} MB). "
                f"Maximum allowed is {MAX_ATTACHMENT_SIZE_MB} MB."
            )

        ctype, encoding = mimetypes.guess_type(attachment_path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        with open(attachment_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(attachment_path),
            )

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)
