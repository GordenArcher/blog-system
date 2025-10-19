
import requests
from django.conf import settings

HUBTEL_SMS_ENDPOINT = getattr(settings, 'HUBTEL_SMS_ENDPOINT', 'https://smsc.hubtel.com/v1/messages/send')
HUBTEL_CLIENT_ID = getattr(settings, 'HUBTEL_CLIENT_ID')
HUBTEL_CLIENT_SECRET = getattr(settings, 'HUBTEL_CLIENT_SECRET')
HUBTEL_SENDER_ID = getattr(settings, 'HUBTEL_SENDER_ID', None)

def send_sms(to: str, content: str, sender: str = None) -> dict:
    """
        Send an SMS via Hubtel.
        `to` should be full international format, e.g. +23324xxxxxxx
        Returns the API response dict or raises exception.
    """
    if sender is None:
        sender = HUBTEL_SENDER_ID

    params = {
        'clientid': HUBTEL_CLIENT_ID,
        'clientsecret': HUBTEL_CLIENT_SECRET,
        'from': sender,
        'to': to,
        'content': content,
    }
    # Hubtel’s quick send uses GET.
    resp = requests.get(HUBTEL_SMS_ENDPOINT, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()
