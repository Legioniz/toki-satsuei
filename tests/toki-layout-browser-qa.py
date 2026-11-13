#!/usr/bin/env python3
"""Responsive layout regression checks for the TOKI SATSUEI microsite."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT
OFFICIAL_LOGO = "https://media.base44.com/images/public/6af6b70d3bc15f40b706af32/30515ce50_Toki_Satsuei_Brushstroke_Emblem.png"
TEST_IMAGE = "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="
FIXTURE = {
    "schema_version": 1, "brand": "TOKI SATSUEI",
    "categories": [{
        "id": "cosplay", "title": "Cosplay",
        "description": "Character portraits, costumes, and details that bring a concept to life.",
        "code": "01", "image_count": 2,
        "albums": [{
            "id": "layout-qa-album",
            "title": "A long album title used to test wrapping at narrow widths",
            "description": "Responsive modal content must remain within its panel.",
            "media": [
                {"type": "image", "src": TEST_IMAGE, "title": "First frame", "alt": "First test frame"},
                {"type": "image", "src": TEST_IMAGE, "title": "Second frame", "alt": "Second test frame"}
            ]
        }]
    }]
}
VIEWPORTS = [
    (320, 568), (360, 740), (390, 844), (430, 932), (460, 800),
    (680, 800), (681, 768), (768, 900), (820, 900), (821, 900),
    (960, 768), (1024, 768), (1280, 800), (1440, 900)
]

class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)
    def log_message(self, *args):
        pass

def boxes(page, selectors):
    return page.evaluate("""(selectors) => selectors.map((selector) => {
      const element = document.querySelector(selector);
      if (!element) return {selector, missing:true};
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return {selector, display:style.display, x:rect.x, y:rect.y, right:rect.right,
        bottom:rect.bottom, width:rect.width, height:rect.height};
    })""", selectors)

def overlaps(a, b):
    return a["width"] > 0 and b["width"] > 0 and a["height"] > 0 and b["height"] > 0 and \
        a["x"] < b["right"] - 1 and a["right"] > b["x"] + 1 and \
        a["y"] < b["bottom"] - 1 and a["bottom"] > b["y"] + 1

def assert_no_pair_overlap(items, label):
    visible = [item for item in items if not item.get("missing") and item["display"] != "none" and item["width"] > 0]
    for index, first in enumerate(visible):
        for second in visible[index + 1:]:
            assert not overlaps(first, second), f"{label}: {first['selector']} overlaps {second['selector']}"

def assert_inside(inner, outer, label):
    assert inner["x"] >= outer["x"] - 1, f"{label}: left edge clipped: {inner}"
    assert inner["right"] <= outer["right"] + 1, f"{label}: right edge clipped: {inner}"
    assert inner["y"] >= outer["y"] - 1, f"{label}: top edge clipped: {inner}"
    assert inner["bottom"] <= outer["bottom"] + 1, f"{label}: bottom edge clipped: {inner}"

def document_width(page, label, width):
    metrics = page.evaluate("""() => ({
      viewport: innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth,
      offenders: [...document.body.querySelectorAll('*')].map(element => {
        const r=element.getBoundingClientRect(), s=getComputedStyle(element);
        return {tag:element.tagName,cls:String(element.className||''),text:(element.innerText||'').slice(0,70),
          left:Math.round(r.left*10)/10,right:Math.round(r.right*10)/10,width:Math.round(r.width*10)/10,
          scrollWidth:element.scrollWidth,clientWidth:element.clientWidth,position:s.position,overflowX:s.overflowX};
      }).filter(item => item.right > innerWidth + .5 || item.left < -.5)
        .sort((a,b) => b.right-a.right).slice(0,12)
    })""")
    assert metrics["document"] <= width + 1, f"{label}: document has horizontal overflow at {width}px: {metrics}"
    assert metrics["body"] <= width + 1, f"{label}: body has horizontal overflow at {width}px: {metrics}"

def check_header(page, width, label):
    header, brand, nav, toggle = boxes(page, [".site-header", ".brand", ".primary-nav", ".menu-toggle"])
    assert not header.get("missing"), f"{label}: site header is missing"
    skip_link = page.locator(".skip-link")
    assert skip_link.get_attribute("href") == "#main-content", f"{label}: keyboard skip link is missing"
    assert page.locator("#main-content").count() == 1, f"{label}: skip-link destination is missing"
    skip_link.focus()
    assert skip_link.evaluate("(node) => getComputedStyle(node).transform === 'matrix(1, 0, 0, 1, 0, 0)'"), f"{label}: skip link is not revealed on keyboard focus"
    logo = page.locator(".brand-mark")
    assert logo.get_attribute("src") == OFFICIAL_LOGO, f"{label}: incorrect logo asset"
    assert logo.get_attribute("alt") == "TOKI SATSUEI official logo", f"{label}: logo alt text is missing"
    header_background = page.locator(".site-header").evaluate("(node) => getComputedStyle(node).backgroundColor")
    announcement_background = page.locator(".announcement").evaluate("(node) => getComputedStyle(node).backgroundColor")
    assert header_background == "rgb(0, 0, 0)", f"{label}: header must match the original logo black"
    assert announcement_background == header_background, f"{label}: announcement strip must match the header and logo"
    page.locator(".site-header").evaluate("(node) => node.classList.add('is-scrolled')")
    scrolled_header_background = page.locator(".site-header").evaluate("(node) => getComputedStyle(node).backgroundColor")
    assert scrolled_header_background == header_background, f"{label}: scrolled header must keep matching the logo black"
    page.locator(".site-header").evaluate("(node) => node.classList.remove('is-scrolled')")
    assert page.locator("link[rel='icon']").get_attribute("href") == OFFICIAL_LOGO, f"{label}: incorrect favicon asset"
    assert page.locator(".brand-copy").count() == 0, f"{label}: duplicate text logo remains beside the official mark"
    assert page.locator(".footer-brand img").get_attribute("src") == OFFICIAL_LOGO, f"{label}: footer does not use the official logo"
    if width <= 820:
        assert toggle["display"] != "none", f"{label}: tablet/mobile menu toggle is hidden at {width}px"
        assert nav["display"] == "none", f"{label}: closed navigation is occupying layout at {width}px"
        page.locator(".menu-toggle").click()
        opened = boxes(page, [".site-header", ".primary-nav"])
        assert opened[1]["display"] != "none", f"{label}: navigation did not open at {width}px"
        assert opened[1]["x"] >= -1 and opened[1]["right"] <= width + 1, f"{label}: open navigation is clipped: {opened[1]}"
        page.locator(".menu-toggle").click()
        page.wait_for_function("!document.querySelector('.primary-nav').classList.contains('is-open')", timeout=2000)
    else:
        assert nav["display"] != "none", f"{label}: desktop navigation is hidden at {width}px"
        assert brand["right"] <= nav["x"] + 1, f"{label}: brand overlaps navigation at {width}px"
        assert nav["right"] <= width + 1, f"{label}: navigation is cut off at {width}px"

def check_footer(page, label):
    items = page.locator(".footer-main > *").evaluate_all("""nodes => nodes.map((element, index) => {
      const r=element.getBoundingClientRect(), s=getComputedStyle(element);
      return {selector:element.className || element.tagName+'-'+index,display:s.display,
        x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};
    })""")
    assert_no_pair_overlap(items, label + " footer")
    viewport_width = page.evaluate("innerWidth")
    for item in items:
        assert item["x"] >= -1 and item["right"] <= viewport_width + 1, \
            f"{label}: footer item is horizontally clipped: {item}"

def check_home(page, width):
    label = f"homepage/{width}"
    document_width(page, label, width)
    check_header(page, width, label)
    hero = page.locator(".hero-opening").bounding_box()
    viewport_height = page.evaluate("innerHeight")
    chrome_height = page.locator(".announcement").evaluate("(node) => node.getBoundingClientRect().height") + page.locator(".site-header").evaluate("(node) => node.getBoundingClientRect().height")
    assert hero and hero["height"] >= max(640, viewport_height - chrome_height - 2), f"{label}: hero does not extend to the available viewport height: hero={hero}, viewport={viewport_height}, chrome={chrome_height}"
    contact = boxes(page, [".contact-panel", ".contact-copy", ".inquiry-form"])
    assert_no_pair_overlap(contact[1:], label + " contact columns")
    for child in contact[1:]:
        assert_inside(child, contact[0], label + " contact panel")
    package_columns = page.locator(".package-grid").evaluate("(node) => getComputedStyle(node).gridTemplateColumns.split(' ').length")
    expected_package_columns = 1 if width <= 520 else (2 if width <= 960 else 4)
    assert package_columns == expected_package_columns, \
        f"{label}: package grid is unbalanced at {width}px: expected {expected_package_columns} columns, got {package_columns}"
    process_grid = page.locator(".process-grid")
    assert process_grid.count() == 1 and process_grid.locator(".process-step").count() == 3, \
        f"{label}: the session process section is incomplete"
    process_box = process_grid.bounding_box()
    process_metrics = process_grid.evaluate("""grid => {
      const r=grid.getBoundingClientRect(), s=getComputedStyle(grid);
      return {left:r.left,right:r.right,width:r.width,scrollWidth:grid.scrollWidth,clientWidth:grid.clientWidth,columns:s.gridTemplateColumns};
    }""")
    assert process_box and process_metrics["scrollWidth"] <= process_metrics["clientWidth"] + 1, \
        f"{label}: session process grid has horizontal overflow: {process_metrics}"
    process_items = process_grid.locator(".process-step").evaluate_all("""nodes => nodes.map(node => {
      const r=node.getBoundingClientRect(), s=getComputedStyle(node);
      return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height,display:s.display};
    })""")
    assert_no_pair_overlap(process_items, label + " session process steps")
    assert all(item["width"] > 0 and item["height"] > 0 for item in process_items), \
        f"{label}: a session process step has no layout size: {process_items}"
    cards = page.locator(".package-card").evaluate_all("""nodes => nodes.map(card => {
      const c=card.getBoundingClientRect();
      return [...card.querySelectorAll('h3,.package-price,ul,.package-link')].map(el => {
        const r=el.getBoundingClientRect();
        return {title:el.className || el.tagName,cardRight:c.right,cardBottom:c.bottom,
          right:r.right,bottom:r.bottom,left:r.left,top:r.top};
      });
    })""")
    for card in cards:
        for item in card:
            assert item["left"] >= -1 and item["right"] <= item["cardRight"] + 1, \
                f"{label}: pricing content exceeds card width: {item}"
            assert item["top"] >= -1 and item["bottom"] <= item["cardBottom"] + 1, \
                f"{label}: pricing content is cut off: {item}"
    check_footer(page, label)

def check_archive(page, width):
    label = f"archive/{width}"
    document_width(page, label, width)
    check_header(page, width, label)
    toolbar = boxes(page, [".library-toolbar", ".library-toolbar-main", ".library-tools"])
    assert_no_pair_overlap(toolbar[1:], label + " archive toolbar")
    assert all(item["width"] <= toolbar[0]["width"] + 1 for item in toolbar[1:]), \
        f"{label}: archive toolbar child exceeds its container: {toolbar}"
    assert page.locator(".footer-socials a").count() == 2, f"{label}: archive footer social links are missing"
    check_footer(page, label)

def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    checks = 0
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context()
            context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            context.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            context.route("https://media.base44.com/**", lambda route: route.abort())
            context.route("https://www.facebook.com/**", lambda route: route.abort())
            home = context.new_page()
            home.goto(base + "/index.html", wait_until="domcontentloaded")
            home.wait_for_selector(".site-header")
            for width, height in VIEWPORTS:
                home.set_viewport_size({"width":width,"height":height})
                home.wait_for_timeout(35)
                check_home(home, width)
                checks += 1

            home.close()
            archive_route_hits = []
            def serve_archive_fixture(route):
                archive_route_hits.append(route.request.url)
                route.fulfill(status=200, content_type="application/json", body=json.dumps(FIXTURE))
            context.route("**/media-library.json*", serve_archive_fixture)
            archive = context.new_page()
            archive_errors = []
            archive.on("pageerror", lambda error: archive_errors.append(str(error)))
            archive.on("console", lambda message: archive_errors.append(f"console {message.type}: {message.text}") if message.type == "error" else None)
            archive.goto(base + "/library.html", wait_until="domcontentloaded")
            archive.bring_to_front()
            archive.wait_for_function(
                "document.querySelector('#library-count')?.textContent !== 'Preparing the archive…'",
                timeout=10000
            )
            assert archive_route_hits, f"Archive fixture was not requested; page errors: {archive_errors}"
            loaded_count = archive.locator("#library-count").inner_text()
            assert "1 ALBUM" in loaded_count and "2 FRAMES" in loaded_count, \
                f"Archive fixture did not populate the expected album cards: {loaded_count!r}; page errors: {archive_errors}"
            archive.wait_for_selector(".album-card", state="attached", timeout=5000)
            for width, height in VIEWPORTS:
                archive.set_viewport_size({"width":width,"height":height})
                archive.wait_for_timeout(35)
                check_archive(archive, width)
                checks += 1

            for width, height in [(320,568),(390,844),(768,900),(1024,768),(1440,900)]:
                archive.set_viewport_size({"width":width,"height":height})
                card = archive.locator(".album-card").first
                card.evaluate("(element) => element.scrollIntoView({block:'center', inline:'nearest', behavior:'instant'})")
                archive.wait_for_function("""() => {
                    const element = document.querySelector(".album-card");
                    if (!element) return false;
                    const rect = element.getBoundingClientRect();
                    return rect.top >= 0 && rect.bottom <= window.innerHeight;
                }""")
                archive.evaluate("""() => {
                    window.__qaCardClicks = 0;
                    window.__qaShowModalCalls = 0;
                    document.addEventListener("click", (event) => {
                        if (event.target.closest(".album-card")) window.__qaCardClicks += 1;
                    }, true);
                    const originalShowModal = HTMLDialogElement.prototype.showModal;
                    HTMLDialogElement.prototype.showModal = function () {
                        window.__qaShowModalCalls += 1;
                        return originalShowModal.call(this);
                    };
                }""")
                card_state = archive.locator(".album-card").first.evaluate("(element) => { const r=element.getBoundingClientRect(); const hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2); return {disabled:element.disabled, tag:element.tagName, text:element.innerText, pointerEvents:getComputedStyle(element).pointerEvents, railClass:element.closest('.album-rail')?.className, centerTarget:hit?.tagName+' '+(typeof hit?.className==='string'?hit.className:'' ), hasFocus:document.hasFocus(), scrollY:window.scrollY, rect:{left:r.left,right:r.right,top:r.top,bottom:r.bottom}}; }")
                card_box = archive.locator(".album-card").first.bounding_box()
                click_x = card_box["x"] + card_box["width"] / 2
                click_y = card_box["y"] + card_box["height"] / 2
                archive.mouse.move(click_x, click_y)
                archive.mouse.down()
                archive.mouse.up()
                dialog_state = archive.locator("#album-dialog").evaluate("(element) => ({open:element.open, display:getComputedStyle(element).display, connected:element.isConnected})")
                event_state = archive.evaluate("() => ({cardClicks:window.__qaCardClicks, showModalCalls:window.__qaShowModalCalls})")
                assert dialog_state["open"] and dialog_state["display"] != "none", \
                    f"archive dialog did not open at {width}px: {dialog_state}; events: {event_state}; card: {card_state}; page errors: {archive_errors}"
                archive.wait_for_timeout(450)
                dialog = boxes(archive, [".album-dialog", ".album-dialog-panel", ".album-media-rail", ".album-dialog-note"])
                for item in dialog[1:]:
                    assert_inside(item, dialog[0], f"archive dialog/{width}")
                panel_metrics = archive.locator(".album-dialog-panel").evaluate(
                    "element => ({scrollHeight:element.scrollHeight,clientHeight:element.clientHeight})"
                )
                assert panel_metrics["scrollHeight"] <= panel_metrics["clientHeight"] + 2, \
                    f"archive dialog content is vertically clipped at {width}px: {panel_metrics}"
                archive.locator(".album-dialog-close").click()
                archive.wait_for_timeout(30)
                checks += 1

            empty_manifest = {
                "schema_version": 1, "brand": "TOKI SATSUEI",
                "categories": [
                    {"id": "cosplay", "title": "Cosplay", "description": "Character portraits and costume details.", "code": "01", "album_count": 0, "image_count": 0, "albums": []},
                    {"id": "portraits", "title": "Portraits", "description": "Individual portraits.", "code": "02", "album_count": 0, "image_count": 0, "albums": []},
                    {"id": "duo-groups", "title": "Duo & groups", "description": "Shared frames and paired characters.", "code": "03", "album_count": 0, "image_count": 0, "albums": []},
                    {"id": "events", "title": "Events", "description": "Conventions and gatherings.", "code": "04", "album_count": 0, "image_count": 0, "albums": []},
                    {"id": "casual-outdoor", "title": "Casual & outdoor", "description": "Unhurried outdoor sessions.", "code": "05", "album_count": 0, "image_count": 0, "albums": []},
                    {"id": "behind-the-scenes", "title": "Behind the camera", "description": "Setup and preparation.", "code": "06", "album_count": 0, "image_count": 0, "albums": []}
                ]
            }
            empty_archive = context.new_page()
            empty_archive.route("**/media-library.json*", lambda route: route.fulfill(
                status=200, content_type="application/json", body=json.dumps(empty_manifest)
            ))
            empty_archive.goto(base + "/library.html", wait_until="domcontentloaded")
            empty_archive.wait_for_function("document.querySelectorAll('.archive-shelf').length === 6")
            assert "0 ALBUMS" in empty_archive.locator("#library-count").inner_text()
            empty_archive.set_viewport_size({"width":390,"height":844})
            document_width(empty_archive, "archive-empty/390", 390)
            shelf_columns = empty_archive.locator(".archive-shelf-grid").evaluate("(node) => getComputedStyle(node).gridTemplateColumns.split(' ').length")
            assert shelf_columns == 1, f"archive-empty/390: category shelves should stack on mobile, got {shelf_columns} columns"
            empty_archive.locator(".archive-shelf").first.click()
            empty_archive.wait_for_function("document.querySelector('.archive-empty-action') !== null")
            empty_archive.locator(".archive-empty-action").click()
            empty_archive.wait_for_function("document.querySelectorAll('.archive-shelf').length === 6")
            empty_archive.close()
            browser.close()
        print(f"PASS TOKI SATSUEI layout QA: {checks} responsive page and dialog checks.")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

if __name__ == "__main__":
    main()
