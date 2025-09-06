import requests
import socket
import os
import time
from typing import Optional

class MailTMEmail:
    def __init__(self, proxy: str, proxy_username: str, proxy_password: str):
        self._session = requests.Session()

        # Configure the authenticated proxy
        hostname, port = proxy.split(":")
        resolved_ip = socket.gethostbyname(hostname)
        proxy_url = f"http://{proxy_username}:{proxy_password}@{resolved_ip}:{port}"
        self._session.proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

        # Mail.tm API base URL
        self.api_base = "https://api.mail.tm"

        print(f"Using proxy for Mail.tm: {proxy_url}")
        response = self._session.get(f"{self.api_base}/domains")
        print(f"Response from domains endpoint: {response.status_code}, {response.text}")

        # Fetch a valid domain
        self.domain = self.get_valid_domain()

        # Create an email account
        account_data = {
            "address": f"test-{os.urandom(8).hex()}@{self.domain}",
            "password": "password",
        }
        response = self._session.post(f"{self.api_base}/accounts", json=account_data)
        if response.status_code != 201:
            raise ValueError(f"Failed to create Mail.tm email: {response.text}")

        data = response.json()
        self.address = data["address"]
        self.token = None
        self.authenticate(account_data["password"])

    def get_valid_domain(self):
        """Fetch valid domains from the Mail.tm API."""
        response = self._session.get(f"{self.api_base}/domains")
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch Mail.tm domains: {response.text}")
        domains = response.json()["hydra:member"]
        if not domains:
            raise ValueError("No valid domains available from Mail.tm.")
        return domains[0]["domain"]  # Return the first valid domain

    def authenticate(self, password):
        """Authenticate the email account to get a token."""
        response = self._session.post(
            f"{self.api_base}/token",
            json={"address": self.address, "password": password},
        )
        if response.status_code != 200:
            raise ValueError(f"Failed to authenticate Mail.tm email: {response.text}")
        self.token = response.json()["token"]
        print(self.token)

    def wait_for_message(self, timeout=60):
        """Poll for a confirmation email."""
        headers = {"Authorization": f"Bearer {self.token}"}
    
        for _ in range(timeout // 5):  # Poll every 10 seconds
            response = self._session.get(f"{self.api_base}/messages", headers=headers)
            print(f"Message retrieval response: {response.status_code}, {response.text}")

            if response.status_code == 200:
                messages = response.json().get("hydra:member", [])
                if messages:
                    # Fetch the first message's full content using its `downloadUrl`
                    message = messages[0]  # Assuming we care about the first message
                    full_download_url = f"{self.api_base}{message['downloadUrl']}"
                    message_details = self._session.get(full_download_url, headers=headers)

                    print(f"Download URL response status: {message_details.status_code}")
                    print(f"Download URL response content: {message_details.text}")

                    if message_details.status_code == 200:
                        try:
                            return message_details.json()  # Parse the JSON if valid
                        except ValueError as e:
                            print(f"Response is not valid JSON. Treating as plain text: {e}")
                            return {"text": message_details.text}  # Return raw text
                    else:
                        print(f"Failed to fetch message content: {message_details.status_code}, {message_details.text}")
            time.sleep(10)

        return None

def get_mail_tm_email(proxy: str, proxy_username: str, proxy_password: str):
    return MailTMEmail(proxy, proxy_username, proxy_password)