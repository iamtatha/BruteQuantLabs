# kite_auth_v2.py — auto-catches redirect token via local server

from dotenv import load_dotenv
import os
load_dotenv()

API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
TOKEN_FILE = "./data/access_token.txt"

# kite_auth_v2.py — fixed version

import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from kiteconnect import KiteConnect
import os

captured_token = None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global captured_token
        params = parse_qs(urlparse(self.path).query)
        if "request_token" in params:
            captured_token = params["request_token"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Auth successful! You can close this tab.</h2>")
        else:
            # browser hit something else (favicon etc.) — just respond OK
            self.send_response(200)
            self.end_headers()

    def log_message(self, *args):
        pass  # silence server logs


def run_server():
    server = HTTPServer(("127.0.0.1", 8080), Handler)
    # Keep serving until we capture the token
    while captured_token is None:
        server.handle_request()
    server.server_close()


kite = KiteConnect(api_key=API_KEY)

t = threading.Thread(target=run_server)
t.daemon = True
t.start()

print("Opening browser for Zerodha login...")
webbrowser.open(kite.login_url())

print("Waiting for authorization...")
t.join(timeout=120)  # wait up to 2 minutes

if captured_token is None:
    print("❌ Timed out — no token received. Check your redirect URL is http://127.0.0.1:8080")
    exit(1)

print(f"✅ Got request_token: {captured_token[:8]}...")

session = kite.generate_session(captured_token, api_secret=API_SECRET)
access_token = session["access_token"]

os.makedirs("./data", exist_ok=True)
with open("./data/access_token.txt", "w") as f:
    f.write(access_token)

print(f"✅ Access token saved: {access_token[:8]}...")