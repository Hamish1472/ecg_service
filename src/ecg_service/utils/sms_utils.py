import time
from vonage import Auth, Vonage
from vonage_sms import SmsMessage, SmsResponse
from ecg_service.config import VONAGE_API_KEY, VONAGE_API_SECRET, EMAIL_SENDER
from ecg_service.utils.email_utils import send_email


def send_sms(
    phone_number: str, filename: str, password: str, sender_id: str = "Cardiologic"
):
    """
    Sends a password via SMS using Vonage.

    Args:
        phone_number (str): Recipient phone number in E.164 format.
        password (str): Password to send.
        sender_id (str): SMS sender ID (default: 'Cardiologic').
    """
    client = Vonage(Auth(api_key=VONAGE_API_KEY, api_secret=VONAGE_API_SECRET))

    message = SmsMessage(
        to=phone_number,
        from_=sender_id,
        text=(
            f"Do Not Reply\n\nPassword to {filename}:\n\n{password}\n\n"
            f"Please check for an email from {EMAIL_SENDER} "
        ),
    )  # type: ignore

    for attempt in range(5):
        response: SmsResponse = client.sms.send(message)
        if response.messages[0].status == "0":
            return True
        time.sleep(3)
    send_email(EMAIL_SENDER, "SMS send error", f"SMS failed for {phone_number}")

    return False


pass
