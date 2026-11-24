"""Orientation QA: portrait and landscape layouts, safe areas, dynamic viewport units, menu behaviour."""
from pathlib import Path
import functools, http.server, socketserver, threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

def main():
    handler = functools.partial(Quiet, directory=str(ROOT))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for page_name in ("index.html", "library.html", "policies.html", "404.html"):
                assert "viewport-fit=cover" in (ROOT / page_name).read_text(), page_name + " lacks viewport-fit=cover"
                for label, (w, h) in {"portrait phone": (390, 844), "landscape phone": (667, 375), "portrait tablet": (820, 1180), "landscape tablet": (1180, 820)}.items():
                    page = browser.new_page(viewport={"width": w, "height": h})
                    errors = []
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.goto(f"{base}/{page_name}")
                    page.wait_for_timeout(500)
                    assert not errors, f"{page_name} {label}: {errors}"
                    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                    assert overflow <= 1, f"{page_name} {label}: horizontal overflow {overflow}px"
                    if page_name != "404.html":
                        expected = "portrait" if h > w else "landscape"
                        assert page.evaluate("document.documentElement.dataset.orientation") == expected, f"{page_name} {label}: wrong data-orientation"
                    if page_name == "index.html" and label == "landscape phone":
                        page.locator(".site-header").evaluate("(node) => { node.classList.remove('is-auto-hidden','is-initial-hidden'); node.style.transform = 'translateY(0)'; }")
                        page.wait_for_timeout(400)
                        header = page.locator(".site-header").bounding_box()["height"]
                        assert header <= 68, f"landscape header too tall: {header}px"
                        page.locator(".menu-toggle").click()
                        page.wait_for_timeout(200)
                        nav = page.locator(".primary-nav").bounding_box()
                        assert nav["y"] + nav["height"] <= h + 1, "open menu runs off a short landscape screen"
                        page.set_viewport_size({"width": 375, "height": 667})
                        page.wait_for_timeout(300)
                        assert page.evaluate("document.documentElement.dataset.orientation") == "portrait"
                        assert not page.locator(".primary-nav.is-open").count(), "menu should close when orientation changes"
                    page.close()
            browser.close()
    print("PASS TOKI orientation QA: 4 pages x 4 screen shapes, safe-area meta, no horizontal overflow, data-orientation, short-landscape header and menu, menu resets on rotation")

if __name__ == "__main__":
    main()
