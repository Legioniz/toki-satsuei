#!/usr/bin/env python3
"""Browser-level adaptive interaction checks for the TOKI SATSUEI site."""
from __future__ import annotations
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

PUBLIC=Path(__file__).resolve().parents[1]
TEST_IMAGE="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="
FIXTURE={"schema_version":1,"brand":"TOKI SATSUEI","categories":[{
 "id":"cosplay","title":"Cosplay","description":"Character portraits and costume details.","code":"01","image_count":3,
 "albums":[{"id":"adaptive-check","title":"Adaptive interaction test album","description":"A multi-frame album used to validate keyboard browsing.",
 "media":[{"type":"image","src":TEST_IMAGE,"title":f"Frame {i}","alt":f"Test frame {i}"} for i in range(1,4)]}]
}]}

def main():
 server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(PUBLIC)))
 thread=Thread(target=server.serve_forever,daemon=True);thread.start()
 base=f"http://127.0.0.1:{server.server_port}";passed=0
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
   context=browser.new_context(viewport={"width":1440,"height":900},has_touch=False)
   context.route("https://fonts.googleapis.com/**",lambda route:route.abort())
   context.route("https://fonts.gstatic.com/**",lambda route:route.abort())
   context.route("https://media.base44.com/**",lambda route:route.abort())
   context.route("https://www.facebook.com/**",lambda route:route.abort())
   home=context.new_page();errors=[]
   home.on("pageerror",lambda error:errors.append(str(error)))
   home.goto(base+"/index.html",wait_until="domcontentloaded")
   home.wait_for_selector(".site-header");home.wait_for_timeout(220)
   hero=home.locator(".hero-opening").bounding_box()
   home.mouse.move(hero["x"]+hero["width"]*.78,hero["y"]+hero["height"]*.3)
   home.wait_for_function("getComputedStyle(document.querySelector('.hero-photo')).translate !== 'none' && getComputedStyle(document.querySelector('.hero-photo')).translate !== '0px 0px'")
   passed+=1

   first=home.locator(".gallery-card:visible").first
   first_title=first.get_attribute("data-title")
   first.scroll_into_view_if_needed();first.click()
   dialog=home.locator("#lightbox")
   assert dialog.evaluate("(el)=>el.open"),"Gallery lightbox did not open"
   assert home.locator(".lightbox-caption strong").inner_text()==first_title
   home.locator(".lightbox-next").click()
   assert home.locator(".lightbox-caption strong").inner_text()!=first_title,"Next button did not change image"
   home.keyboard.press("ArrowLeft")
   assert home.locator(".lightbox-caption strong").inner_text()==first_title,"Left arrow did not return to first image"
   assert home.locator(".lightbox-position").inner_text()=="01 / 04"
   home.locator(".lightbox-close").click()
   assert not dialog.evaluate("(el)=>el.open")
   passed+=1

   home.locator('.filter-button[data-filter="behind"]').click()
   home.wait_for_function("document.querySelectorAll('.gallery-card:not([hidden])').length===1")
   home.locator('.filter-button[data-filter="all"]').click()
   home.wait_for_function("document.querySelectorAll('.gallery-card:not([hidden])').length===4")
   passed+=1

   home.locator('.package-link[data-session="Duo / group session"]').click()
   assert home.locator('select[name="session"]').input_value()=="Duo / group session"
   passed+=1

   home.evaluate("window.scrollTo({top:0,behavior:'instant'})")
   home.set_viewport_size({"width":390,"height":844})
   menu=home.locator(".menu-toggle");menu.click()
   assert menu.get_attribute("aria-expanded")=="true"
   home.keyboard.press("Escape")
   assert menu.get_attribute("aria-expanded")=="false"
   menu.click()
   home.evaluate("document.querySelector('.hero-opening').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
   assert menu.get_attribute("aria-expanded")=="false","Outside click did not close mobile navigation"
   passed+=1

   reduced=context.new_page();reduced.emulate_media(reduced_motion="reduce")
   reduced.goto(base+"/index.html",wait_until="domcontentloaded");reduced.wait_for_timeout(100)
   reduced_state=reduced.locator(".hero-photo").evaluate("(el)=>getComputedStyle(el).transition")
   assert "0s" in reduced_state or reduced_state.startswith("none"),"Reduced-motion preference did not disable hero parallax transition"
   reduced.close();home.close();passed+=1

   archive=context.new_page();archive_errors=[]
   archive.on("pageerror",lambda error:archive_errors.append(str(error)))
   archive.route("**/media-library.json*",lambda route:route.fulfill(status=200,content_type="application/json",body=json.dumps(FIXTURE)))
   archive.goto(base+"/library.html",wait_until="domcontentloaded")
   archive.wait_for_selector(".album-card")
   card=archive.locator(".album-card").first;card.click()
   album_dialog=archive.locator("#album-dialog")
   assert album_dialog.evaluate("(el)=>el.open"),"Album dialog did not open"
   archive.keyboard.press("End")
   archive.wait_for_function("document.querySelector('#album-dialog-position').textContent==='03 / 03'")
   archive.keyboard.press("Home")
   archive.wait_for_function("document.querySelector('#album-dialog-position').textContent==='01 / 03'")
   archive.locator(".album-dialog-close").click()
   assert not album_dialog.evaluate("(el)=>el.open")
   assert card.evaluate("(el)=>el===document.activeElement"),"Album dialog did not restore focus to its launch card"
   archive.set_viewport_size({"width":390,"height":844})
   archive.locator(".menu-toggle").click()
   assert archive.locator(".menu-toggle").get_attribute("aria-expanded")=="true"
   archive.keyboard.press("Escape")
   assert archive.locator(".menu-toggle").get_attribute("aria-expanded")=="false"
   assert not archive_errors,"Archive JavaScript errors: "+"; ".join(archive_errors)
   passed+=1
   browser.close()
  print(f"PASS TOKI SATSUEI adaptive interaction QA: {passed} interaction groups.")
 finally:
  server.shutdown();server.server_close();thread.join(timeout=2)

if __name__=="__main__":main()
