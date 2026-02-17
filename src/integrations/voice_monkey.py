"""Voice Monkey API client for sending announcements to Alexa devices."""
import requests
from typing import Optional


class VoiceMonkeyClient:
    """Client for sending TTS announcements via Voice Monkey API."""

    def __init__(self, api_url: str, enabled: bool = True):
        """
        Initialize Voice Monkey client.

        Args:
            api_url: Full Voice Monkey API URL with token and device parameters
            enabled: Whether announcements are enabled
        """
        self.api_url = api_url
        self.enabled = enabled

    def announce(self, message: str) -> bool:
        """
        Send announcement to all Alexa devices.

        Args:
            message: Text to announce

        Returns:
            True if announcement was sent successfully, False otherwise
        """
        if not self.enabled:
            print(f"[Announcements disabled] {message}")
            return True

        try:
            # Voice Monkey API uses GET with 'text' parameter
            # Build complete URL manually since base URL already has parameters
            separator = "&" if "?" in self.api_url else "?"
            full_url = f"{self.api_url}{separator}text={requests.utils.quote(message)}"

            print(f"[Sending to Voice Monkey] {message}")
            print(f"[URL] {full_url[:80]}...")  # Print first 80 chars of URL for debugging

            response = requests.get(full_url, timeout=5)

            if response.status_code == 200:
                print(f"[Announcement sent successfully] Status: {response.status_code}")
                return True
            else:
                print(f"[Announcement failed] Status {response.status_code}")
                print(f"[Response] {response.text[:200]}")  # Print first 200 chars of response
                return False

        except requests.exceptions.Timeout:
            print(f"[Announcement timeout] {message}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"[Announcement error] {e}: {message}")
            return False
        except Exception as e:
            print(f"[Unexpected error] {e}: {message}")
            return False

    def test_connection(self) -> bool:
        """
        Test connection to Voice Monkey API.

        Returns:
            True if connection successful, False otherwise
        """
        return self.announce("Voice Monkey connection test")
