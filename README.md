# Mobile Money Payment API (Burkina Faso)

API non officiel pour les paiements mobiles Orange Money, Moov Money et Ligdicash au Burkina Faso


## Avant l'installation

1. Obtenir un compte API avec Orange/Moov/Ligdicash (username, password, phonenumber, certificats, ....)
2. Installer les certificats fournis par l'opérateur s'il y'en a


## Dépendances

- python >= 3.10
- requests >= 2.33.0

## Installation

```bash
pip install git+https://github.com/parice02/bf-mobilemoney.git # with pip
poetry add git+https://github.com/parice02/bf-mobilemoney.git # with poetry
```


## Cas d'utilisation

### exemple de paiement avec Orange Money (Burkina Faso)

```python
from mobilemoney import validate_om_prod_payment



url = "<Your OM API URL>"
username = "<Your OM API username>"
password = "<Your OM API password>"
phonenumber = "<Your OM API phone number>"
customer_phone = "<Your customer phone number>"
customer_otp = "<Your customer OTP code>"
amount = 100  # entier
message = "<a message for user>"
reference = None  # générée automatiquement si None


response = validate_om_prod_payment(
    username, password, phonenumber, customer_phone, customer_otp, amount, message,
    reference, url,
)
print(response)  # {"status": ..., "message": ..., "trans_id": ...}
```


### exemple de paiement avec Moov Money (Burkina Faso)

```python
from mobilemoney import MMPayment

# exemple de paiement avec moov money

url = "<Your Moov API URL>"
username = "<Your Moov API username>"
password = "<Your Moov API password>"
customer_phone = "<Your customer phone number>"
customer_otp = "<Your customer OTP code>"
amount = 100  # entier
message = "<a message for user>"
otp_trans_id = "<TRANS ID received during the last OTP generation>"

with MMPayment(url, username, password) as moov:
    response = moov.send_otp(customer_phone, amount)
    print(response)

    response = moov.resend_otp(customer_phone, amount)
    print(response)

    response = moov.validate_payment(
        customer_phone, customer_otp, amount, message, otp_trans_id
    )
    print(response)
```

La vérification SSL est activée par défaut. Si la passerelle utilise un certificat
auto-signé, passez le chemin du certificat fourni par l'opérateur :
`verify_ssl="/chemin/vers/ca.pem"`.

## Contribution

Les contributions sont libres.


## Reste à faire

1. Implémenter des tests
2. Écrire une documentation
3. Publier sur pypi
