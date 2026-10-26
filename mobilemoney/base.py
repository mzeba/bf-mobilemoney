import logging
import re
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, Optional, Union

# Keys whose values must never appear in logs (compared case-insensitively)
SENSITIVE_KEYS = {"password", "api_password", "otp", "authorization", "apikey"}
_SENSITIVE_XML_RE = re.compile(
    r"(<(api_password|otp)>)(.*?)(</\2>)", re.IGNORECASE | re.DOTALL
)


def redact(value: Any) -> Any:
    """
    Return a copy of value with secrets masked, for safe logging.

    Handles dicts (JSON payloads, headers), lists and XML strings.
    """
    if isinstance(value, dict):
        return {
            k: "***" if str(k).lower() in SENSITIVE_KEYS else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return _SENSITIVE_XML_RE.sub(r"\1***\4", value)
    return value


class BasePayment(object):
    """
    Base class for mobile money payment implementations.

    This class provides common functionality for mobile money providers
    including credential management and basic validation.

    Attributes:
        phonenumber (str): The merchant phone number
        username (str): API username for authentication
        password (str): API password for authentication
    """

    def __init__(self, phonenumber: str = "", username: str = "", password: str = ""):
        """
        Initialize BasePayment instance.

        Args:
            phonenumber (str, optional): Merchant phone number. Defaults to "".
            username (str, optional): API username. Defaults to "".
            password (str, optional): API password. Defaults to "".

        Raises:
            ValueError: If any parameter is not a string type.
        """
        if phonenumber is not None and not isinstance(phonenumber, str):
            raise ValueError("value 'phonenumber' must be type of 'str'")

        if not isinstance(username, str):
            raise ValueError("value 'username' must be type of 'str'")

        if not isinstance(password, str):
            raise ValueError(
                "value 'password' must be type of 'str'"
            )  # Fixed bug: was 'username'

        self._username = username
        self._password = password
        self._phonenumber = phonenumber

        # Initialize HTTP session for connection pooling and performance
        self._session = requests.Session()
        self._logger = logging.getLogger(
            self.__class__.__module__ + "." + self.__class__.__name__
        )

    @property
    def phonenumber(self):
        """Get the merchant phone number."""
        return self._phonenumber

    @phonenumber.setter
    def phonenumber(self, value):
        """Set the merchant phone number."""
        if value is not None and not isinstance(value, str):
            raise ValueError("Phone number must be a string")
        self._phonenumber = value

    @property
    def username(self):
        """Get the API username."""
        return self._username

    @username.setter
    def username(self, value):
        """Set the API username."""
        if not isinstance(value, str):
            raise ValueError("Username must be a string")
        self._username = value

    @property
    def password(self):
        """Get the API password."""
        return self._password

    @password.setter
    def password(self, value):
        """Set the API password."""
        if not isinstance(value, str):
            raise ValueError("Password must be a string")
        self._password = value

    def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, Dict[str, Any]]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        auth: Optional[HTTPBasicAuth] = None,
        verify_ssl: bool = True,
        timeout: int = 30,
    ) -> requests.Response:
        """
        Make HTTP request using session with proper error handling.

        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE, etc.)
            url (str): Request URL
            headers (Dict[str, str], optional): Request headers
            data (Union[str, Dict[str, Any]], optional): Request body data
            json_data (Dict[str, Any], optional): JSON request body
            auth (HTTPBasicAuth, optional): Authentication object
            verify_ssl (bool, optional): Whether to verify SSL certificates. Defaults to True.
            timeout (int, optional): Request timeout in seconds. Defaults to 30.

        Returns:
            requests.Response: HTTP response object

        Raises:
            requests.RequestException: If request fails
            ValueError: If method or url is invalid
        """
        if not isinstance(method, str) or not method.strip():
            raise ValueError("Method must be a non-empty string")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("URL must be a non-empty string")

        method = method.upper()

        # Set default headers
        request_headers = {
            "User-Agent": "bf-mobilemoney/1.0",
            "Accept": "application/json, application/xml, text/plain, */*",
        }
        if headers:
            request_headers.update(headers)

        self._logger.debug(f"Making {method} request to: {url}")
        self._logger.debug(f"Headers: {redact(request_headers)}")
        if data:
            self._logger.debug(f"Data: {redact(data)}")
        if json_data:
            self._logger.debug(f"JSON: {redact(json_data)}")

        try:
            response = self._session.request(
                method=method,
                url=url,
                headers=request_headers,
                data=data,
                json=json_data,
                auth=auth,
                verify=verify_ssl,
                timeout=timeout,
            )

            self._logger.info(f"{method} {url} - Status: {response.status_code}")
            self._logger.debug(f"Response headers: {dict(response.headers)}")
            self._logger.debug(f"Response content: {response.text}")

            return response

        except requests.exceptions.Timeout:
            self._logger.error(f"Request timeout for {method} {url}")
            raise
        except requests.exceptions.ConnectionError:
            self._logger.error(f"Connection error for {method} {url}")
            raise
        except requests.exceptions.HTTPError as e:
            self._logger.error(f"HTTP error for {method} {url}: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error for {method} {url}: {e}")
            raise

    def close_session(self):
        """
        Close the HTTP session to free resources.
        Call this when the payment object is no longer needed.
        """
        if hasattr(self, "_session") and self._session:
            self._session.close()
            self._logger.debug("HTTP session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes session."""
        self.close_session()
