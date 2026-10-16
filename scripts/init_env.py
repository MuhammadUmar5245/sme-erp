"""Create .env from .env.example with random secrets (used by `make up` on first run)."""
import base64
import re
import secrets
from pathlib import Path

root = Path(__file__).resolve().parent.parent
text = (root / ".env.example").read_text()
values = {
    "DJANGO_SECRET_KEY": secrets.token_urlsafe(48),
    "FIELD_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    "POSTGRES_PASSWORD": secrets.token_urlsafe(18),
    "POWERBI_READER_PASSWORD": secrets.token_urlsafe(18),
}
for name, value in values.items():
    text = re.sub(rf"^{name}=.*$", f"{name}={value}", text, flags=re.M)
(root / ".env").write_text(text)
print("Created .env with random secrets (keep this file private).")
