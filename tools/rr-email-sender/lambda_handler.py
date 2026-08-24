"""
rr-email-sender · Envía correos masivos a usuarios de ricardoruiz.co vía SES.

Invocación:
  aws lambda invoke --function-name rr-email-sender \
    --payload fileb://payload.json --cli-binary-format raw-in-base64-out out.json

Payload (JSON):
  {
    "subject": "Asunto del correo",
    "html": "<html>... con {{firstName}} y {{unsubscribeUrl}} ...</html>",
    "dryRun": false,                      # opcional, true = no manda
    "limitTo": ["a@x.com", "b@y.com"],    # opcional, restringe a estos correos
    "from": "Ricardo Ruiz <ricardo@ricardoruiz.co>",  # opcional
    "replyTo": "reruizc@gmail.com",       # opcional
    "rateDelaySec": 1.1                   # opcional, default 1.1s (sandbox 1/s)
  }
"""
import os
import json
import time
import hmac
import hashlib
import base64
import urllib.request
import boto3
from botocore.exceptions import ClientError

WORKER_BASE = os.environ["WORKER_BASE_URL"].rstrip("/")
ADMIN_API_KEY = os.environ["ADMIN_API_KEY"]
UNSUB_SECRET = os.environ["UNSUB_SECRET"]
DEFAULT_FROM = os.environ.get("DEFAULT_FROM", "Ricardo Ruiz <ricardo@ricardoruiz.co>")
DEFAULT_REPLY_TO = os.environ.get("DEFAULT_REPLY_TO", "reruizc@gmail.com")

ses = boto3.client("sesv2", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def fetch_users():
    req = urllib.request.Request(
        f"{WORKER_BASE}/admin/users-list",
        headers={
            "X-Admin-Api-Key": ADMIN_API_KEY,
            "Accept": "application/json",
            "User-Agent": "rr-email-sender/1.0 (+https://ricardoruiz.co)",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data.get("ok"):
        raise RuntimeError(f"Worker /admin/users-list error: {data.get('error', 'unknown')}")
    return data.get("users", [])


def unsub_url(email):
    e_enc = base64.urlsafe_b64encode(email.lower().encode("utf-8")).decode("ascii").rstrip("=")
    sig = hmac.new(UNSUB_SECRET.encode("utf-8"), email.lower().encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    return f"{WORKER_BASE}/unsub?e={e_enc}&t={sig}"


def first_name(user):
    name = (user.get("name") or "").strip()
    if not name:
        return ""
    return name.split()[0]


def personalize(html, user):
    first = first_name(user)
    out = html
    if first:
        out = out.replace("{{firstName}}", first)
        out = out.replace("Hola ,", f"Hola {first},")
    else:
        out = out.replace(" {{firstName}}", "")
        out = out.replace("{{firstName}}", "")
    out = out.replace("{{unsubscribeUrl}}", unsub_url(user["email"]))
    out = out.replace("{{email}}", user["email"])
    return out


def send_one(subject, html, from_addr, reply_to, user):
    body = personalize(html, user)
    unsub = unsub_url(user["email"])
    try:
        kwargs = {
            "FromEmailAddress": from_addr,
            "Destination": {"ToAddresses": [user["email"]]},
            "Content": {
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": body, "Charset": "UTF-8"}},
                }
            },
            "ReplyToAddresses": [reply_to],
            "EmailTags": [{"Name": "campaign", "Value": os.environ.get("CAMPAIGN_TAG", "newsletter")}],
        }
        ses.send_email(**kwargs)
        return {"email": user["email"], "ok": True, "unsubUrl": unsub}
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        msg = e.response.get("Error", {}).get("Message", str(e))
        return {"email": user["email"], "ok": False, "error": f"{code}: {msg}"}
    except Exception as e:
        return {"email": user["email"], "ok": False, "error": str(e)}


def handler(event, context):
    subject = (event.get("subject") or "").strip()
    html = event.get("html") or ""
    dry_run = bool(event.get("dryRun", False))
    limit_to = event.get("limitTo")
    from_addr = event.get("from") or DEFAULT_FROM
    reply_to = event.get("replyTo") or DEFAULT_REPLY_TO
    rate_delay = float(event.get("rateDelaySec", 1.1))

    if not subject:
        return {"ok": False, "error": "subject required"}
    if not html:
        return {"ok": False, "error": "html required"}

    try:
        users = fetch_users()
    except Exception as e:
        return {"ok": False, "error": f"fetch_users failed: {e}"}

    print(f"Fetched {len(users)} users from worker")

    if limit_to:
        limit_set = {e.lower() for e in limit_to if isinstance(e, str)}
        users = [u for u in users if (u.get("email") or "").lower() in limit_set]
        print(f"Filtered to {len(users)} after limitTo")

    users = [u for u in users if u.get("email") and "@" in u["email"]]
    users = [u for u in users if not u.get("unsubscribed")]
    print(f"After unsub/email filter: {len(users)}")

    if dry_run:
        return {
            "ok": True,
            "dryRun": True,
            "wouldSend": len(users),
            "sample": [
                {"email": u["email"], "name": u.get("name"), "unsubUrl": unsub_url(u["email"])}
                for u in users[:3]
            ],
        }

    sent, failed, errors = 0, 0, []
    for i, u in enumerate(users):
        if i > 0:
            time.sleep(rate_delay)
        r = send_one(subject, html, from_addr, reply_to, u)
        if r["ok"]:
            sent += 1
            print(f"OK {r['email']}")
        else:
            failed += 1
            errors.append(r)
            print(f"FAIL {r['email']}: {r['error']}")

    return {"ok": True, "sent": sent, "failed": failed, "errors": errors, "total": len(users)}
