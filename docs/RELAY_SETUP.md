# Relay Server Setup Guide

The relay server is required for SignBridge to work. It joins your Telegram call as a participant, captures the hearing person's audio, and streams it to the Android app.

## Requirements

- Python 3.10+
- A server reachable from your phone (VPS, home server, or localhost with port forwarding)
- Telegram account credentials (api_id + api_hash)

## Get Telegram Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your phone number
3. Click "Create new application"
4. Fill in:
   - App title: `SignBridge`
   - Short name: `signbridge`
   - Platform: `Android`
   - URL: `https://localhost`
5. Copy your `api_id` (number) and `api_hash` (string)

> **Note:** The my.telegram.org site is sometimes buggy. If you get "ERROR", try Chrome, wait 5 minutes and retry, or clear cookies.

## Install Dependencies

```bash
cd relay
pip install -r requirements.txt
```

## Configure

Set environment variables:

```bash
export TELEGRAM_PHONE="+1234567890"   # The phone number for the relay account
export TELEGRAM_APP_ID="12345"         # api_id from my.telegram.org
export TELEGRAM_APP_HASH="abc123..."   # api_hash from my.telegram.org
export LISTEN_HOST="0.0.0.0"
export LISTEN_PORT="8080"
```

Or create a `.env` file (already in `.gitignore`):
```
TELEGRAM_PHONE=+1234567890
TELEGRAM_APP_ID=12345
TELEGRAM_APP_HASH=abc123...
```

## First Run (Phone Authorization)

The first time you start the relay, Pyrogram will ask you to authorize the account:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

Follow the prompts — enter the code sent to your Telegram app. A session file will be created and reused on subsequent starts.

> **Tip:** Use a dedicated Telegram account for the relay, not your personal account. The hearing person will see this account join the call.

## Test It Works

```bash
curl http://localhost:8080/health
# Expected: {"status": "ok"}
```

## Configure the Android App

In the SignBridge app:
- Setup screen → enter the relay URL (e.g., `http://192.168.1.10:8080`)
- Or Settings → Path B — Relay Server → enter URL

## Deploy on a VPS (optional)

Any $5/month VPS works. Example with systemd:

```ini
# /etc/systemd/system/signbridge-relay.service
[Unit]
Description=SignBridge Relay Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/signbridge/relay
Environment="TELEGRAM_PHONE=+1234567890"
Environment="TELEGRAM_APP_ID=12345"
Environment="TELEGRAM_APP_HASH=abc123..."
ExecStart=/opt/signbridge/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable signbridge-relay
sudo systemctl start signbridge-relay
```

## What the Hearing Person Sees

The relay joins the call as a Telegram user account. The hearing person will see a notification:
> "SignBridge joined the call"

They will see the relay account as a participant. Make sure the deaf user informs the hearing person about this beforehand.
