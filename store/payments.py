"""
Thin wrapper around the Paystack API.

Paystack (https://paystack.com) is used here because a single integration
covers both card payments and Ghanaian Mobile Money (MTN, Telecel,
AirtelTigo) — the customer picks their network on Paystack's own hosted
checkout page, so we never handle raw card or MoMo PIN details ourselves.

Flow:
    1. `initialize_transaction()` asks Paystack for a checkout URL.
    2. We redirect the customer to that URL to pay.
    3. Paystack redirects them back to our `callback_url` with a
       `?reference=...` query param.
    4. `verify_transaction()` asks Paystack whether that reference was
       actually paid before we trust it and mark the order paid.

Never trust the redirect alone — always verify server-to-server, since a
user could edit the URL or the redirect could be spoofed.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PAYSTACK_BASE_URL = 'https://api.paystack.co'
REQUEST_TIMEOUT_SECONDS = 15


class PaystackError(Exception):
    """Raised when Paystack can't be reached or rejects a request."""


def _headers():
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError(
            'PAYSTACK_SECRET_KEY is not configured. Add it to your .env file — '
            'see .env.example. You can get test keys from your Paystack dashboard.'
        )
    return {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }


def initialize_transaction(*, email, amount_cedis, reference, callback_url):
    """
    Ask Paystack to create a checkout session.

    `amount_cedis` is a Decimal/float in whole cedis (e.g. 125.50);
    Paystack's API expects the smallest currency unit (pesewas), so it's
    converted here.

    Returns the `authorization_url` the customer should be redirected to.
    Raises PaystackError on any failure.
    """
    payload = {
        'email': email,
        'amount': int(round(float(amount_cedis) * 100)),
        'currency': 'GHS',
        'reference': reference,
        'callback_url': callback_url,
        'channels': ['card', 'mobile_money'],
    }
    try:
        response = requests.post(
            f'{PAYSTACK_BASE_URL}/transaction/initialize',
            json=payload,
            headers=_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.error('Paystack initialize request failed: %s', exc)
        raise PaystackError('Could not reach the payment provider. Please try again.') from exc

    data = response.json()
    if not response.ok or not data.get('status'):
        logger.error('Paystack initialize rejected: %s', data)
        raise PaystackError(data.get('message', 'Payment could not be started.'))

    return data['data']['authorization_url']


def verify_transaction(reference):
    """
    Ask Paystack whether `reference` was actually paid.

    Returns the transaction data dict on success (status == 'success').
    Raises PaystackError if the reference is unknown, unpaid, or the
    request fails.
    """
    try:
        response = requests.get(
            f'{PAYSTACK_BASE_URL}/transaction/verify/{reference}',
            headers=_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.error('Paystack verify request failed: %s', exc)
        raise PaystackError('Could not reach the payment provider to confirm your payment.') from exc

    data = response.json()
    if not response.ok or not data.get('status'):
        logger.error('Paystack verify rejected: %s', data)
        raise PaystackError(data.get('message', 'Could not verify this payment.'))

    tx = data['data']
    if tx.get('status') != 'success':
        raise PaystackError(f"Payment was not successful (status: {tx.get('status')}).")

    return tx
