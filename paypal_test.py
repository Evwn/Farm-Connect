import requests
import base64

# PayPal API credentials
client_id = "AcrRNp9TnRox_Bfy6apyCcbNVzNo8buRaTF1S5N5UMKr909l96V5OBNbIc6fSFhp1M1xnG0QKfuPGCOq"
client_secret = "EMvHXheIGtE6rP8aeG8UqwpsHAM9nyGDIOlRmCMmqWvVwRvaDFHtorrmsQNZxJwDzI6TIwiKEUmOdxeS"

# Create Basic Auth header
credentials = f"{client_id}:{client_secret}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()

# PayPal API endpoint
url = 'https://api.sandbox.paypal.com/v1/oauth2/token'

# Headers
headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json',
    'Accept-Language': 'en_US',
    'Authorization': f'Basic {encoded_credentials}',
}

# Data
data = {
    'grant_type': 'client_credentials'
}

try:
    print(f"Attempting to connect to {url}...")
    print(f"Using client_id: {client_id}")
    print(f"Authorization header: Basic {encoded_credentials[:10]}...")
    response = requests.post(url, headers=headers, data=data)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}") 