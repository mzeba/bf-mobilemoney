from importlib.metadata import PackageNotFoundError, version

from mobilemoney.base import BasePayment
from mobilemoney.orangemoney import (
    GenericPayment as OMGenericPayement,
    Payment as OMPayment,
    DevPayment as OMDevPayment,
)

from mobilemoney.moovmoney import (
    GenericPayment as MMGenericPayement,
    Payment as MMPayment,
    DevPayment as MMDevPayment,
)
from mobilemoney.ligdicash import (
    GenericPaymentWithRedirect as LigdicashGenericPaymentWithRedirect,
    Payment as LigdicashPaymentWithRedirect,
)

try:
    # Single source of truth: the version declared in pyproject.toml
    __version__ = version("bf-mobilemoney")
except PackageNotFoundError:  # source checkout that was never installed
    __version__ = "unknown"


def send_otp_for_moov_money_payment(
    username: str,
    password: str,
    customer_phone: str,
    amount: int,
    url: str,
    reference: str = None,
    verify_ssl: bool = True,
    is_resend: bool = False,
):
    payment = MMPayment(url, username, password)
    if is_resend:
        return payment.resend_otp(customer_phone, amount, verify_ssl, reference)
    else:
        return payment.send_otp(customer_phone, amount, verify_ssl, reference)


def validate_moov_prod_payment(
    username: str,
    password: str,
    customer_phone: str,
    customer_otp: str,
    amount: int,
    message: str,
    otp_trans_id: str,
    reference: str,
    url,
    verify_ssl: bool = True,
):
    payment = MMPayment(url, username, password)
    return payment.validate_payment(
        customer_phone,
        customer_otp,
        amount,
        message,
        otp_trans_id,
        reference,
        verify_ssl=verify_ssl,
    )


def validate_moov_dev_payment(
    username: str,
    password: str,
    customer_phone: str,
    customer_otp: str,
    amount: int,
    message: str,
    otp_trans_id,
    reference: str,
    url: str,
    verify_ssl: bool = True,
):
    payment = MMDevPayment(url, username, password)
    return payment.validate_payment(
        customer_phone,
        customer_otp,
        amount,
        message,
        otp_trans_id,
        reference,
        verify_ssl=verify_ssl,
    )


def validate_om_prod_payment(
    username: str,
    password: str,
    phonenumber: str,
    customer_phone: str,
    customer_otp: str,
    amount: int,
    message: str,
    reference: str,
    url,
    verify_ssl: bool = True,
):
    payment = OMPayment(url, phonenumber, username, password)
    return payment.validate_payment(
        customer_phone, customer_otp, amount, message, reference, verify_ssl=verify_ssl
    )


def validate_om_dev_payment(
    username: str,
    password: str,
    phonenumber: str,
    customer_phone: str,
    customer_otp: str,
    amount: int,
    message: str,
    reference: str,
    url,
    verify_ssl: bool = True,
):
    payment = OMDevPayment(url, phonenumber, username, password)
    return payment.validate_payment(
        customer_phone, customer_otp, amount, message, reference, verify_ssl=verify_ssl
    )


def validate_ligdicash_payment(
    api_key,
    api_token,
    command,
    url,
    verify_ssl: bool = True,
):
    """
    Validate a payment
        - command param must be :
            {
                "invoice": {
                    "items": [
                    {
                        "name": "Nom du produit ou Service",
                        "description": " Description du produit ou Service ",
                        "quantity": 1,
                        "unit_price": 100,
                        "total_price": 100
                    }
                    ],
                    "total_amount": 100,
                    "devise": "XOF",
                    "description": " Description du contenu de la facture(Achat de jus de fruits)",
                    "customer": "",
                    "customer_firstname": "Nom du client",
                    "customer_lastname": "Prénom du client",
                    "customer_email": "tester@gligdicash.com",
                    "external_id": "",
                    "otp": ""
                },
                "store": {
                    "name": "Nom de votre site ou de votre boutique",
                    "website_url": "url de votre site ou de votre boutique"
                },
                "actions": {
                    "cancel_url": "http://localhost",
                    "return_url": "http://localhost",
                    "callback_url": "http://localhost"
                },
                "custom_data": {
                    "transaction_id": "2021000000001",
                    "logfile": "202110210048426170b8ea884a9",
                    "developpeur": "kaboretidiane"
                }
            }

        - response will be:
            {
                "response_code": "00",
                "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZF9pbnZvaWNlIjoiMTU0NTkwMTIiLCJzdGFydF9kYXRlIjoiMjAyMy0wMi0yMyAxODoyNDoxMiIsImV4cGlyeV9kYXRlIjoxNjc3MjU5NDUyfQ.U9GwpBQpZwW1YdWD_0Zla9-Uy-sUV7zDn4Nobtfc33M",
                "response_text": "https://client.ligdicash.com/directpayment/invoice/eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZF9pbnZvaWNlIjoiMTU0NTkwMTIiLCJzdGFydF9kYXRlIjoiMjAyMy0wMi0yMyAxODoyNDoxMiIsImV4cGlyeV9kYXRlIjoxNjc3MjU5NDUyfQ.U9GwpBQpZwW1YdWD_0Zla9-Uy-sUV7zDn4Nobtfc33M",
                "description": "",
                "custom_data": {
                    "transaction_id": "2021000000001",
                    "logfile": "2023022318241263f7af4ccc792",
                    "developpeur": "kaboretidiane",
                },
                "wiki": "https://client.ligdicash.com/wiki/createInvoice",
            }
    """
    payment = LigdicashPaymentWithRedirect(url, username=api_key, password=api_token)
    return payment.validate_payment(command, verify_ssl=verify_ssl)


def verify_ligdicash_payment_token(
    api_key, api_token, payment_token, url, verify_ssl: bool = True
):
    payment = LigdicashPaymentWithRedirect(url, username=api_key, password=api_token)
    return payment.verify_token(url, payment_token, verify_ssl=verify_ssl)
