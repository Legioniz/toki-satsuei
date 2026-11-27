"""Each page links exactly one stylesheet (its bundle), and the committed bundles match their sources."""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "index.html": "toki-home.css",
    "booking.html": "toki-home.css",
    "library.html": "toki-archive.css",
    "policies.html": "toki-policies.css",
    "404.html": "toki-404.css",
    "admin.html": "toki-admin.css",
    "client-gallery.html": "toki-client.css",
}

def main():
    for page, bundle in EXPECTED.items():
        links = re.findall(r'<link rel="stylesheet" href="\./([a-z0-9-]+\.css)">', (ROOT / page).read_text(encoding="utf-8"))
        assert links == [bundle], f"{page} should link only {bundle}, found {links}"
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build-css.py"), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    print("PASS TOKI CSS bundle QA: one stylesheet per page, bundles match their sources")

if __name__ == "__main__":
    main()
