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
FIXTURE={"schema_version":2,"brand":"TOKI SATSUEI","categories":[{
 "id":"cosplay","title":"Cosplay","description":"Character portraits and costume details.","code":"01","image_count":3,"video_count":0,"media_count":3,
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
   home.wait_for_function("document.documentElement.classList.contains('motion-system-ready') && window.TokiMotion && document.querySelector('.gallery-card.motion-item')")
   assert home.evaluate("typeof window.TokiMotion.closeDialog === 'function' && typeof window.TokiMotion.setMenuOpen === 'function'"), "Shared menu/dialog transition helpers are missing"
   assert home.locator(".motion-item").count() >= 10, "Shared motion system did not prepare enough homepage content"
   gallery_transition=home.locator(".gallery-card").first.evaluate("(el)=>getComputedStyle(el).transitionDuration")
   assert "0.46s" in gallery_transition, "Gallery cards are missing the shared interaction transition"
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
   home.wait_for_function("document.querySelector('.lightbox-image').getAnimations().some(animation=>animation.playState==='running')",timeout=2000)
   home.keyboard.press("ArrowLeft")
   assert home.locator(".lightbox-caption strong").inner_text()==first_title,"Left arrow did not return to first image"
   assert home.locator(".lightbox-position").inner_text()=="01 / 04"
   home.locator(".lightbox-close").click()
   assert dialog.evaluate("(el)=>el.getAnimations().some(animation=>animation.playState==='running')"),"Lightbox exit transition did not start"
   home.wait_for_function("!document.querySelector('#lightbox').open")
   assert not dialog.evaluate("(el)=>el.open")
   passed+=1

   home.locator('.filter-button[data-filter="behind"]').click()
   home.wait_for_function("document.querySelectorAll('.gallery-card:not([hidden])').length===1")
   home.locator('.filter-button[data-filter="all"]').click()
   home.wait_for_function("document.querySelectorAll('.gallery-card:not([hidden])').length===4")
   passed+=1

   home.wait_for_function("document.querySelector('.facebook-feed-filter')",timeout=8000)
   feed_filter=home.locator(".facebook-feed-filter").last
   feed_filter.scroll_into_view_if_needed();feed_filter.click()
   assert home.locator(".facebook-post-list").evaluate("(el)=>el.getAnimations().some(animation=>animation.playState==='running')"),"Facebook feed refresh did not animate"
   passed+=1

   name_field=home.locator('input[name="name"]')
   name_field.fill("Motion QA");name_field.fill("")
   assert name_field.evaluate("(el)=>el.matches(':user-invalid')"),"Inquiry form validation feedback did not activate"
   passed+=1

   duo_card=home.locator('.package-card[data-session="Duo / group session"]')
   duo_card.click()
   assert duo_card.get_attribute("aria-pressed")=="true"
   assert home.locator('select[name="session"]').input_value()=="Duo / group session"
   home.wait_for_function("document.querySelector('#form-status').textContent.includes('Duo Session')")
   assert "Duo Session" in home.locator("#form-status").inner_text()
   assert home.locator('.package-card[aria-pressed="true"]').count()==1
   portrait_card=home.locator('.package-card[data-session="Cosplay photoshoot"]')
   portrait_card.focus()
   home.keyboard.press("Enter")
   assert portrait_card.get_attribute("aria-pressed")=="true"
   assert home.locator('select[name="session"]').input_value()=="Cosplay photoshoot"
   passed+=1

   home.evaluate("window.scrollTo({top:0,behavior:'instant'})")
   home.set_viewport_size({"width":390,"height":844})
   menu=home.locator(".menu-toggle");menu.click()
   assert menu.get_attribute("aria-expanded")=="true"
   home.wait_for_function("document.querySelector('.primary-nav').getAnimations().length > 0")
   icon_transform=home.locator(".menu-toggle span").first.evaluate("(el)=>getComputedStyle(el).transform")
   assert icon_transform != "none", "Mobile menu icon did not animate into its open state"
   home.keyboard.press("Escape")
   assert menu.get_attribute("aria-expanded")=="false"
   assert home.locator(".primary-nav").evaluate("(el)=>el.getAnimations().some(animation=>animation.playState==='running')"),"Mobile menu exit transition did not start"
   home.wait_for_function("!document.querySelector('.primary-nav').classList.contains('is-open')")
   menu.click()
   home.evaluate("document.querySelector('.hero-opening').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
   assert menu.get_attribute("aria-expanded")=="false","Outside click did not close mobile navigation"
   passed+=1

   reduced=context.new_page();reduced.emulate_media(reduced_motion="reduce")
   reduced.goto(base+"/index.html",wait_until="domcontentloaded");reduced.wait_for_timeout(100)
   reduced.wait_for_function("document.documentElement.classList.contains('motion-system-ready')")
   reduced_opacity=reduced.locator(".gallery-card").first.evaluate("(el)=>getComputedStyle(el).opacity")
   assert reduced_opacity == "1", "Reduced-motion mode left a content card hidden"
   reduced_state=reduced.locator(".hero-photo").evaluate("(el)=>getComputedStyle(el).transition")
   assert "0s" in reduced_state or reduced_state.startswith("none"),"Reduced-motion preference did not disable hero parallax transition"
   reduced.close();home.close();passed+=1

   archive=context.new_page();archive_errors=[]
   archive.on("pageerror",lambda error:archive_errors.append(str(error)))
   archive.route("**/media-library.json*",lambda route:route.fulfill(status=200,content_type="application/json",body=json.dumps(FIXTURE)))
   archive.goto(base+"/library.html",wait_until="domcontentloaded")
   archive.wait_for_selector(".album-card")
   archive.wait_for_function("document.querySelector('.album-card')?.classList.contains('motion-item')")
   assert archive.locator(".album-card.motion-item").count() >= 1, "Archive cards were not enrolled in shared motion"
   card=archive.locator(".album-card").first;card.click()
   album_dialog=archive.locator("#album-dialog")
   assert album_dialog.evaluate("(el)=>el.open"),"Album dialog did not open"
   archive.keyboard.press("End")
   archive.wait_for_function("document.querySelector('#album-dialog-position').textContent==='03 / 03'")
   archive.keyboard.press("Home")
   archive.wait_for_function("document.querySelector('#album-dialog-position').textContent==='01 / 03'")
   archive.locator(".album-dialog-close").click()
   assert album_dialog.evaluate("(el)=>el.getAnimations().some(animation=>animation.playState==='running')"),"Album dialog exit transition did not start"
   archive.wait_for_function("!document.querySelector('#album-dialog').open")
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
