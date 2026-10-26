import logging
import requests
import xml.etree.ElementTree as ET

from mobilemoney.base import BasePayment
from mobilemoney.utils import get_reference

# Configure logging
logger = logging.getLogger(__name__)


class GenericPayment(BasePayment):
    """
    Orange Money payment implementation.

    This class handles Orange Money API interactions including
    payment validation and XML request/response parsing.

    Attributes:
        url (str): The Orange Money API endpoint URL
    """

    def __init__(self, url="", phonenumber="", username="", password=""):
        """
        Initialize Orange Money payment instance.

        Args:
            url (str, optional): API endpoint URL. Defaults to "".
            phonenumber (str, optional): Merchant phone number. Defaults to "".
            username (str, optional): API username. Defaults to "".
            password (str, optional): API password. Defaults to "".

        Raises:
            ValueError: If url is not a string.
        """
        super().__init__(phonenumber, username, password)

        if not isinstance(url, str):
            raise ValueError("value 'url' must be type of 'str'")
        if not url.strip():
            logger.warning("Empty URL provided for Orange Money API")
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
        libel: str,
        reference=None,
    ):
        """
        Parse payment request data into XML format for Orange Money API.

        Args:
            customer_phone (str): Customer's phone number
            customer_otp (str): Customer's OTP code
            amount (int): Payment amount
            libel (str): Payment description/label
            reference (str, optional): Transaction reference. Auto-generated if None.

        Returns:
            str: XML string formatted for Orange Money API

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
        if not isinstance(libel, str) or not libel.strip():
            raise ValueError("Label must be a non-empty string")
        if reference is not None and not isinstance(reference, str):
            raise ValueError("Reference must be a string or None")

        logger.info(
            f"Creating payment request for phone: {customer_phone}, amount: {amount}"
        )

        root = ET.Element("COMMAND")

        # Ajouter les éléments enfants à l'élément racine
        ET.SubElement(root, "TYPE").text = "OMPREQ"
        ET.SubElement(root, "customer_msisdn").text = f"{customer_phone}"
        ET.SubElement(root, "merchant_msisdn").text = self._phonenumber
        ET.SubElement(root, "api_username").text = self._username
        ET.SubElement(root, "api_password").text = self._password
        ET.SubElement(root, "amount").text = f"{amount}"
        ET.SubElement(root, "PROVIDER").text = "101"
        ET.SubElement(root, "PROVIDER2").text = "101"
        ET.SubElement(root, "PAYID").text = "12"
        ET.SubElement(root, "PAYID2").text = "12"
        ET.SubElement(root, "otp").text = f"{customer_otp}"
        ET.SubElement(root, "reference_number").text = libel
        ET.SubElement(root, "ext_txn_id").text = reference or get_reference()

        tree = ET.ElementTree(root)
        xml_string = ET.tostring(root, encoding="utf-8").decode("utf-8")

        return xml_string

    def parse_result(self, result: str):
        """
        Parse XML response from Orange Money API.

        Args:
            result (str): Raw XML response from API

        Returns:
            dict: Parsed response with status, message, and transaction ID
        """
        try:
            # Validate input
            if not isinstance(result, str):
                error_msg = f"Result must be a string, got {type(result).__name__}"
                logger.error(error_msg)
                return {
                    "message": error_msg,
                    "status": "OM-500",
                    "trans_id": "Error",
                }

            if not result.strip():
                error_msg = "Empty response received from API"
                logger.error(error_msg)
                return {
                    "message": error_msg,
                    "status": "OM-500",
                    "trans_id": "Error",
                }

            # Parse XML with proper error handling
            try:
                root = ET.fromstring("<root>" + result + "</root>")
            except ET.ParseError as e:
                error_msg = (
                    f"Erreur de parsing XML: {str(e)} - Réponse: {result[:100]}..."
                )
                logger.error(error_msg)
                return {
                    "message": error_msg,
                    "status": "OM-501",
                    "trans_id": "Error",
                }

            # Extract elements with null checks
            status = root.find("status")
            message = root.find("message")
            trans_id = root.find("transID")

            # Check if all required elements are present
            missing_fields = []
            if status is None:
                missing_fields.append("status")
            if message is None:
                missing_fields.append("message")
            if trans_id is None:
                missing_fields.append("transID")

            if missing_fields:
                error_msg = (
                    f"Champs manquants dans la réponse API: {', '.join(missing_fields)}"
                )
                logger.error(f"{error_msg} - Réponse complète: {result}")
                return {
                    "message": error_msg,
                    "status": "OM-500",
                    "trans_id": "Error",
                }

            # Validate that text content exists
            if not status.text or not message.text or not trans_id.text:
                empty_fields = []
                if not status.text:
                    empty_fields.append("status")
                if not message.text:
                    empty_fields.append("message")
                if not trans_id.text:
                    empty_fields.append("transID")

                error_msg = (
                    f"Champs vides dans la réponse API: {', '.join(empty_fields)}"
                )
                logger.error(f"{error_msg} - Réponse complète: {result}")
                return {
                    "message": error_msg,
                    "status": "OM-500",
                    "trans_id": "Error",
                }

            # Successfully parsed response
            response = {
                "status": status.text.strip(),
                "message": message.text.strip(),
                "trans_id": trans_id.text.strip(),
            }
            logger.info(f"Successfully parsed API response: {response}")
            return response

        except Exception as e:
            error_msg = f"Erreur inattendue lors du parsing: {str(e)}"
            logger.exception(error_msg)  # Logs full traceback
            return {
                "message": error_msg,
                "status": "OM-502",
                "trans_id": "Error",
            }

    def validate_payment(
        self,
        customer_phone: str,
        customer_otp: str,
        amount: int,
        message: str,
        reference=None,
        verify_ssl=True,
    ):
        """
        Validate and process payment through Orange Money API.

        Args:
            customer_phone (str): Customer's phone number
            customer_otp (str): Customer's OTP code
            amount (int): Payment amount
            message (str): Payment description
            reference (str, optional): Transaction reference. Auto-generated if None.
            verify_ssl (bool, optional): Whether to verify SSL certificates. Defaults to True.

        Returns:
            dict: API response with status, message, and transaction ID

        Raises:
            requests.RequestException: If network request fails
            ValueError: If input validation fails
        """
        try:
            # Validate URL configuration
            if not self._url:
                error_msg = "API URL not configured"
                self._logger.error(error_msg)
                raise ValueError(error_msg)

            # Prepare request
            headers = {"content-type": "application/xml"}

            try:
                data = self.parse_query(
                    customer_phone, customer_otp, amount, message, reference
                )
            except ValueError as e:
                # Input validation errors from parse_query
                self._logger.error(f"Validation error: {e}")
                return {
                    "message": f"Erreur de validation des données: {str(e)}",
                    "status": "OM-400",
                    "trans_id": "Error",
                }
            except Exception as e:
                self._logger.error(f"Error building request: {e}")
                return {
                    "message": f"Erreur de construction de la requête: {str(e)}",
                    "status": "OM-500",
                    "trans_id": "Error",
                }

            # Make HTTP request
            try:
                response = self._make_request(
                    method="POST",
                    url=self._url,
                    headers=headers,
                    data=data,
                    verify_ssl=verify_ssl,
                )
            except Exception as e:
                error_type = type(e).__name__
                self._logger.error(f"{error_type} during request: {e}")

                # ConnectTimeout is both a Timeout and a ConnectionError, and
                # SSLError is a ConnectionError, so the order of these checks matters
                if isinstance(e, requests.exceptions.Timeout):
                    return {
                        "message": f"Timeout de l'API Orange Money ({self._url})",
                        "status": "OM-503",
                        "trans_id": "Error",
                    }
                elif isinstance(e, requests.exceptions.SSLError):
                    return {
                        "message": f"Erreur SSL/Certificat: {str(e)}",
                        "status": "OM-495",
                        "trans_id": "Error",
                    }
                elif isinstance(e, requests.exceptions.ConnectionError):
                    return {
                        "message": f"Erreur de connexion à l'API Orange Money ({self._url})",
                        "status": "OM-504",
                        "trans_id": "Error",
                    }
                else:
                    return {
                        "message": f"Erreur de requête ({error_type}): {str(e)}",
                        "status": "OM-506",
                        "trans_id": "Error",
                    }

            # Validate HTTP status code
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                status_code = (
                    response.status_code
                    if hasattr(response, "status_code")
                    else "Unknown"
                )
                self._logger.error(f"HTTP {status_code} error: {e}")

                # Try to parse error response anyway
                if hasattr(response, "text") and response.text:
                    result = self.parse_result(response.text)
                    # Add HTTP status info to result
                    if (
                        result.get("status") == "OM-500"
                    ):  # Default error from parse_result
                        result["status"] = f"OM-505-{status_code}"
                        result["message"] = (
                            f"Erreur HTTP {status_code}: {result.get('message', str(e))}"
                        )
                    return result
                else:
                    return {
                        "message": f"Erreur HTTP {status_code}: {str(e)}",
                        "status": "OM-505",
                        "trans_id": "Error",
                    }

            # Parse successful response
            try:
                if not hasattr(response, "text") or not response.text:
                    self._logger.error("Empty response from API")
                    return {
                        "message": "Réponse vide de l'API Orange Money",
                        "status": "OM-500",
                        "trans_id": "Error",
                    }

                result = self.parse_result(response.text)
                self._logger.info(
                    f"Payment validation completed: {result.get('status')}"
                )
                return result

            except Exception as e:
                self._logger.exception(f"Error parsing response: {e}")
                return {
                    "message": f"Erreur de traitement de la réponse: {str(e)}",
                    "status": "OM-502",
                    "trans_id": "Error",
                }

        except ValueError as e:
            # Configuration or validation errors
            self._logger.error(f"Validation error: {e}")
            return {
                "message": f"Erreur de validation: {str(e)}",
                "status": "OM-400",
                "trans_id": "Error",
            }
        except Exception as e:
            # Catch-all for unexpected errors
            self._logger.exception(f"Unexpected error in validate_payment: {e}")
            return {
                "message": f"Erreur inattendue ({type(e).__name__}): {str(e)}",
                "status": "OM-506",
                "trans_id": "Error",
            }


class DevPayment(GenericPayment):
    """
    Development environment Orange Money payment implementation.

    This class is intended for use in development/testing environments.
    """

    def __init__(self, url, phonenumber="", username="", password=""):
        """
        Initialize development Orange Money payment instance.

        Args:
            url (str): Development API endpoint URL
            phonenumber (str, optional): Merchant phone number. Defaults to "".
            username (str, optional): Development API username. Defaults to "".
            password (str, optional): Development API password. Defaults to "".
        """
        super().__init__(url, phonenumber, username, password)
        logger.info("Initialized Orange Money DevPayment instance")


class Payment(GenericPayment):
    """
    Production environment Orange Money payment implementation.

    This class is intended for use in production environments.
    """

    def __init__(self, url, phonenumber="", username="", password=""):
        """
        Initialize production Orange Money payment instance.

        Args:
            url (str): Production API endpoint URL
            phonenumber (str, optional): Merchant phone number. Defaults to "".
            username (str, optional): Production API username. Defaults to "".
            password (str, optional): Production API password. Defaults to "".
        """
        super().__init__(url, phonenumber, username, password)
        logger.info("Initialized Orange Money Payment instance")
