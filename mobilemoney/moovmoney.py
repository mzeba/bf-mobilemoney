import logging
import requests
from requests.auth import HTTPBasicAuth

from mobilemoney.base import BasePayment
from mobilemoney.utils import get_reference

# Configure logging
logger = logging.getLogger(__name__)


SEND_OTP_OPTIONS = [
    "process-create-mror-otp",
    "process-mror-resend-otp",
]


class GenericPayment(BasePayment):
    """
    Moov Money payment implementation.

    This class handles Moov Money API interactions including
    OTP sending, resending, and payment validation.

    Attributes:
        url (str): The Moov Money API endpoint URL
    """

    def __init__(self, url="", username="", password=""):
        """
        Initialize Moov Money payment instance.

        Args:
            url (str, optional): API endpoint URL. Defaults to "".
            username (str, optional): API username. Defaults to "".
            password (str, optional): API password. Defaults to "".

        Raises:
            ValueError: If url is not a string.
        """
        super().__init__(None, username, password)

        if not isinstance(url, str):
            raise ValueError("value 'url' must be type of 'str'")
        if not url.strip():
            logger.warning("Empty URL provided for Moov Money API")
        self._url = url

    @property
    def url(self):
        """Get the API endpoint URL."""
        return self._url

    @url.setter
    def url(self, value):
        """Set the API endpoint URL."""
        if not isinstance(value, str):
            raise ValueError("URL must be a string")
        self._url = value

    def parse_query(
        self,
        customer_phone: str,
        customer_otp: str,
        amount: int,
        message: str,
        otp_trans_id: str,
        reference: str = None,
    ):
        """
        Parse payment request data for Moov Money API.

        Args:
            customer_phone (str): Customer's phone number
            customer_otp (str): Customer's OTP code
            amount (int): Payment amount
            message (str): Payment description/remarks
            otp_trans_id (str): OTP transaction ID
            reference (str, optional): Transaction reference. Auto-generated if None.

        Returns:
            dict: Request payload formatted for Moov Money API

        Raises:
            ValueError: If any parameter has invalid type or value
        """
        # Validate inputs
        if not isinstance(customer_phone, str) or not customer_phone.strip():
            raise ValueError("Customer phone number must be a non-empty string")
        if not isinstance(customer_otp, str) or not customer_otp.strip():
            raise ValueError("Customer OTP must be a non-empty string")
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError("Amount must be a positive integer")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message must be a non-empty string")
        if not isinstance(otp_trans_id, str) or not otp_trans_id.strip():
            raise ValueError("OTP transaction ID must be a non-empty string")
        if reference is not None and not isinstance(reference, str):
            raise ValueError("Reference must be a string or None")

        # Normalize phone number (add country code if not present)
        phone_number = customer_phone
        if not phone_number.startswith("226"):
            phone_number = f"226{customer_phone}"

        logger.info(
            f"Creating payment request for phone: {phone_number}, amount: {amount}"
        )
        return {
            "request-id": reference or get_reference(),
            "destination": phone_number,
            "amount": amount,
            "remarks": message,
            "extended-data": {
                "module": "MERCHOTPPAY",
                "otp": customer_otp,
                "ext1": "Vous avez payé pour 1",
                "ext2": "Vous avez payé pour 2",
                "trans-id": otp_trans_id,
            },
        }

    def _request_error_response(self, error: Exception, context: str):
        """
        Map an exception raised while sending a request to an error response.

        Args:
            error (Exception): Exception raised by _make_request
            context (str): Short description of the request, for logging

        Returns:
            dict: Error response with 'error' and 'status' keys
        """
        self._logger.error(f"{type(error).__name__} during {context}: {error}")

        # ConnectTimeout is both a Timeout and a ConnectionError, and SSLError
        # is a ConnectionError, so the order of these checks matters
        if isinstance(error, requests.exceptions.Timeout):
            return {
                "error": f"Timeout de l'API Moov Money ({self._url})",
                "status": "MM-503",
            }
        if isinstance(error, requests.exceptions.SSLError):
            return {
                "error": f"Erreur SSL/Certificat: {str(error)}",
                "status": "MM-495",
            }
        if isinstance(error, requests.exceptions.ConnectionError):
            return {
                "error": f"Erreur de connexion à l'API Moov Money ({self._url})",
                "status": "MM-504",
            }
        return {
            "error": f"Erreur de requête ({type(error).__name__}): {str(error)}",
            "status": "MM-506",
        }

    def _http_error_response(self, response, error: Exception, context: str):
        """
        Build an error response from a non-2xx HTTP response.

        Args:
            response (requests.Response): Response with an error status code
            error (Exception): HTTPError raised by raise_for_status
            context (str): Short description of the request, for logging

        Returns:
            dict: Error response, merged with the API's JSON error body if any
        """
        status_code = response.status_code
        self._logger.error(f"HTTP {status_code} error in {context}: {error}")

        error_response = {"status": f"MM-505-{status_code}"}
        try:
            error_data = response.json()
        except ValueError:
            error_data = None

        if isinstance(error_data, dict):
            error_response["error"] = error_data.get(
                "message", error_data.get("error", str(error))
            )
            # Include all error details from API
            error_response.update(error_data)
        else:
            error_response["error"] = f"Erreur HTTP {status_code}: {str(error)}"
        return error_response

    def _send_otp(
        self,
        customer_phone: str,
        amount: int,
        verify_ssl=False,
        option="",
        reference: str = None,
    ):
        """
        Internal method to send or resend OTP.

        Args:
            customer_phone (str): Customer's phone number
            amount (int): Payment amount
            verify_ssl (bool, optional): Whether to verify SSL certificates. Defaults to False.
            option (str): OTP operation type (create or resend)
            reference (str, optional): Transaction reference. Auto-generated if None.

        Returns:
            dict: API response

        Raises:
            ValueError: If option is not valid or inputs are invalid
            requests.RequestException: If network request fails
        """
        # Validate option
        if option not in SEND_OTP_OPTIONS:
            error_msg = (
                f"'option' parameter must be one of '{','.join(SEND_OTP_OPTIONS)}'"
            )
            self._logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate inputs
        try:
            if not isinstance(customer_phone, str) or not customer_phone.strip():
                raise ValueError("Customer phone number must be a non-empty string")
            if not isinstance(amount, int) or amount <= 0:
                raise ValueError("Amount must be a positive integer")
            if reference is not None and not isinstance(reference, str):
                raise ValueError("Reference must be a string or None")
        except ValueError as e:
            self._logger.error(f"Input validation error: {e}")
            return {
                "error": f"Erreur de validation: {str(e)}",
                "status": "MM-400",
            }

        # Normalize phone number
        phone_number = customer_phone
        if not phone_number.startswith("226"):
            phone_number = f"226{customer_phone}"

        try:
            # Validate URL configuration
            if not self._url:
                error_msg = "API URL not configured"
                self._logger.error(error_msg)
                return {
                    "error": error_msg,
                    "status": "MM-500",
                }

            # Prepare request data
            data = {
                "request-id": reference or get_reference(),
                "destination": phone_number,
                "amount": amount,
                "remarks": "Merchant Payment with OTP",
                "extended-data": {"module": "MERCHOTPPAY"},
            }

            headers = {
                "content-type": "application/json",
                "command-id": option,
            }

            auth = HTTPBasicAuth(self._username, self._password)

            # Make HTTP request
            try:
                response = self._make_request(
                    method="POST",
                    url=self._url,
                    headers=headers,
                    json_data=data,
                    auth=auth,
                    verify_ssl=verify_ssl,
                )
            except Exception as e:
                return self._request_error_response(e, "OTP request")

            # Validate HTTP status code
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                return self._http_error_response(response, e, "OTP request")

            # Parse successful response
            try:
                if not hasattr(response, "text") or not response.text:
                    self._logger.error("Empty response from OTP API")
                    return {
                        "error": "Réponse vide de l'API Moov Money",
                        "status": "MM-500",
                    }

                result = response.json()
                self._logger.info(
                    f"OTP request completed successfully: {result.get('status', 'OK')}"
                )
                return result

            except ValueError as e:
                # JSON parsing error
                self._logger.error(f"JSON parsing error: {e}")
                return {
                    "error": f"Erreur de format de réponse JSON: {str(e)}",
                    "status": "MM-502",
                    "raw_response": (
                        response.text[:200] if hasattr(response, "text") else None
                    ),
                }
            except Exception as e:
                self._logger.exception(f"Error parsing OTP response: {e}")
                return {
                    "error": f"Erreur de traitement de la réponse: {str(e)}",
                    "status": "MM-502",
                }

        except Exception as e:
            # Catch-all for unexpected errors
            self._logger.exception(f"Unexpected error in _send_otp: {e}")
            return {
                "error": f"Erreur inattendue ({type(e).__name__}): {str(e)}",
                "status": "MM-506",
            }

    def send_otp(
        self,
        customer_phone: str,
        amount: int,
        verify_ssl=False,
        reference: str = None,
    ):
        """
        Send OTP to customer for payment authorization.

        Args:
            customer_phone (str): Customer's phone number
            amount (int): Payment amount
            verify_ssl (bool, optional): Whether to verify SSL certificates. Defaults to False.
            reference (str, optional): Transaction reference. Auto-generated if None.

        Returns:
            dict: API response containing OTP sending status
        """
        logger.info(f"Sending OTP to {customer_phone} for amount {amount}")
        return self._send_otp(
            customer_phone, amount, verify_ssl, SEND_OTP_OPTIONS[0], reference
        )

    def resend_otp(
        self,
        customer_phone: str,
        amount: int,
        verify_ssl=False,
        reference: str = None,
    ):
        """
        Resend OTP to customer for payment authorization.

        Args:
            customer_phone (str): Customer's phone number
            amount (int): Payment amount
            verify_ssl (bool, optional): Whether to verify SSL certificates. Defaults to False.
            reference (str, optional): Transaction reference. Auto-generated if None.

        Returns:
            dict: API response containing OTP resending status
        """
        logger.info(f"Resending OTP to {customer_phone} for amount {amount}")
        return self._send_otp(
            customer_phone, amount, verify_ssl, SEND_OTP_OPTIONS[1], reference
        )

    def validate_payment(
        self,
        customer_phone: str,
        customer_otp: str,
        amount: int,
        message: str,
        otp_trans_id: str,
        reference: str = None,
        verify_ssl=False,
    ):
        """
        Validate and process payment through Moov Money API.

        Args:
            customer_phone (str): Customer's phone number
            customer_otp (str): Customer's OTP code
            amount (int): Payment amount
            message (str): Payment description
            otp_trans_id (str): OTP transaction ID from send_otp response
            verify_ssl (bool, optional): Whether to verify SSL certificates. Defaults to False.
            reference (str, optional): Transaction reference. Auto-generated if None.

        Returns:
            dict: API response with payment validation status

        Raises:
            requests.RequestException: If network request fails
            ValueError: If input validation fails
        """
        try:
            # Validate URL configuration
            if not self._url:
                error_msg = "API URL not configured"
                self._logger.error(error_msg)
                return {
                    "error": error_msg,
                    "status": "MM-500",
                }

            # Prepare request
            headers = {
                "content-type": "application/json",
                "command-id": "process-commit-otppay",
            }

            # Build payload with validation
            try:
                payload = self.parse_query(
                    customer_phone,
                    customer_otp,
                    amount,
                    message,
                    otp_trans_id,
                    reference,
                )
            except ValueError as e:
                # Input validation errors from parse_query
                self._logger.error(f"Validation error: {e}")
                return {
                    "error": f"Erreur de validation des données: {str(e)}",
                    "status": "MM-400",
                }
            except Exception as e:
                self._logger.error(f"Error building payment request: {e}")
                return {
                    "error": f"Erreur de construction de la requête: {str(e)}",
                    "status": "MM-500",
                }

            auth = HTTPBasicAuth(self._username, self._password)

            # Make HTTP request
            try:
                response = self._make_request(
                    method="POST",
                    url=self._url,
                    headers=headers,
                    json_data=payload,
                    auth=auth,
                    verify_ssl=verify_ssl,
                )
            except Exception as e:
                return self._request_error_response(e, "payment request")

            # Validate HTTP status code
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                return self._http_error_response(response, e, "payment request")

            # Parse successful response
            try:
                if not hasattr(response, "text") or not response.text:
                    self._logger.error("Empty response from payment API")
                    return {
                        "error": "Réponse vide de l'API Moov Money",
                        "status": "MM-500",
                    }

                result = response.json()

                # Log success or business errors
                if "error" in result or result.get("status", "").lower() in [
                    "failed",
                    "error",
                ]:
                    self._logger.warning(
                        f"Payment failed with business error: {result}"
                    )
                else:
                    self._logger.info(
                        f"Payment validation completed successfully: {result.get('status', 'OK')}"
                    )

                return result

            except ValueError as e:
                # JSON parsing error
                self._logger.error(f"JSON parsing error: {e}")
                return {
                    "error": f"Erreur de format de réponse JSON: {str(e)}",
                    "status": "MM-502",
                    "raw_response": (
                        response.text[:200] if hasattr(response, "text") else None
                    ),
                }
            except Exception as e:
                self._logger.exception(f"Error parsing payment response: {e}")
                return {
                    "error": f"Erreur de traitement de la réponse: {str(e)}",
                    "status": "MM-502",
                }

        except ValueError as e:
            # Configuration or validation errors
            self._logger.error(f"Validation error: {e}")
            return {
                "error": f"Erreur de validation: {str(e)}",
                "status": "MM-400",
            }
        except Exception as e:
            # Catch-all for unexpected errors
            self._logger.exception(f"Unexpected error in validate_payment: {e}")
            return {
                "error": f"Erreur inattendue ({type(e).__name__}): {str(e)}",
                "status": "MM-506",
            }


class DevPayment(GenericPayment):
    """
    Development environment Moov Money payment implementation.

    This class is intended for use in development/testing environments.
    """

    def __init__(self, url, username="", password=""):
        """
        Initialize development Moov Money payment instance.

        Args:
            url (str): Development API endpoint URL
            username (str, optional): Development API username. Defaults to "".
            password (str, optional): Development API password. Defaults to "".
        """
        super().__init__(url, username, password)
        logger.info("Initialized Moov Money DevPayment instance")


class Payment(GenericPayment):
    """
    Production environment Moov Money payment implementation.

    This class is intended for use in production environments.
    """

    def __init__(self, url, username="", password=""):
        """
        Initialize production Moov Money payment instance.

        Args:
            url (str): Production API endpoint URL
            username (str, optional): Production API username. Defaults to "".
            password (str, optional): Production API password. Defaults to "".
        """
        super().__init__(url, username, password)
        logger.info("Initialized Moov Money Payment instance")
