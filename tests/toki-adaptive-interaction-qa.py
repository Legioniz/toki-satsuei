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
   home=context.new_page();errors=[]
   home.on("pageerror",lambda error:errors.append(str(error)))
   home.goto(base+"/index.html",wait_until="domcontentloaded")
   home.wait_for_selector(".site-header",state="attached")
   home.wait_for_function("document.documentElement.classList.contains('motion-system-ready') && window.TokiMotion && document.querySelector('.gallery-card.motion-item')")
   assert home.locator(".site-header").evaluate("(node)=>node.classList.contains('is-auto-hidden') && node.inert"), "Homepage masthead must remain hidden and inert while the hero is in view"
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
   home.locator(".lightbox-next").click()
   third_full=home.locator(".gallery-card:visible").nth(2).get_attribute("data-full")
   third_title=home.locator(".gallery-card:visible").nth(2).get_attribute("data-title")
   home.wait_for_function("(expected)=>document.querySelector('.lightbox-image')?.getAttribute('src')===expected",arg=third_full)
   assert home.locator(".lightbox-caption strong").inner_text()==third_title,"Rapid next navigation applied a stale lightbox frame"
   home.keyboard.press("ArrowLeft")
   second_title=home.locator(".gallery-card:visible").nth(1).get_attribute("data-title")
   assert home.locator(".lightbox-caption strong").inner_text()==second_title,"Left arrow did not move to the previous image"
   home.keyboard.press("ArrowLeft")
   assert home.locator(".lightbox-caption strong").inner_text()==first_title,"Second left arrow did not return to the first image"
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

   assert home.locator(".facebook-section").count()==0,"Retired social embed rail remains on the homepage"
   assert home.locator('a[href="https://www.facebook.com/tokisatsuiephotography/"]').count()>=1,"Official Facebook link was removed"
   assert home.locator('a[href="https://www.instagram.com/tokisatsuiephotography/"]').count()>=1,"Official Instagram link was removed"
   passed+=1

   assert home.locator("#inquiry-form").count()==0,"Homepage should not embed the booking form"
   assert home.locator('a.nav-contact[href="./booking.html"]').count()==1,"Homepage booking navigation should open the booking page"
   booking_page=context.new_page()
   booking_page.goto(base+"/booking.html",wait_until="domcontentloaded")
   name_field=booking_page.locator('input[name="name"]')
   name_field.fill("Motion QA");name_field.fill("")
   name_field.blur()
   assert name_field.evaluate("(el)=>el.matches(':user-invalid')"),"Booking page validation feedback did not activate"
   booking_page.close()
   passed+=1

   launcher=context.new_page()
   launcher.goto(base+"/index.html#sessions",wait_until="domcontentloaded")
   duo_card=launcher.locator('.package-card[data-session="Duo Session"]')
   duo_card.locator(".package-link").click()
   launcher.wait_for_function("location.pathname.endsWith('/booking.html')")
   assert launcher.locator('select[name="session"]').input_value()=="Duo Session","Duo package was not carried into booking"
   launcher.goto(base+"/index.html#sessions",wait_until="domcontentloaded")
   portrait_card=launcher.locator('.package-card[data-session="Toki Portraits"]')
   portrait_card.locator(".package-link").focus()
   launcher.keyboard.press("Enter")
   launcher.wait_for_function("location.pathname.endsWith('/booking.html')")
   assert launcher.locator('select[name="session"]').input_value()=="Toki Portraits","Keyboard package selection did not prefill booking"
   launcher.close()
   passed+=1

   home.evaluate("""() => {
     const scroller=document.scrollingElement;
     scroller.style.setProperty("scroll-behavior","auto","important");
     scroller.scrollTop=0;
   }""")
   home.set_viewport_size({"width":390,"height":844})
   home.wait_for_timeout(120)
   assert home.locator(".site-header").evaluate("(node)=>node.classList.contains('is-auto-hidden')"), "Homepage masthead must stay hidden over the mobile hero"
   # A revealed masthead must remain visible when its menu opens, even while the hero lock is active.
   header=home.locator(".site-header")
   header.evaluate("""node=>{
     node.classList.remove("is-auto-hidden","is-initial-hidden");
     node.setAttribute("aria-hidden","false");
     node.inert=false;
   }""")
   menu=home.locator(".menu-toggle");menu.click()
   home.wait_for_function("""() => {
     const header=document.querySelector(".site-header");
     const nav=document.querySelector(".primary-nav");
     const h=header?.getBoundingClientRect(), n=nav?.getBoundingClientRect();
     return nav?.classList.contains("is-open") &&
       header?.getAttribute("aria-hidden")==="false" && !header.inert &&
       !header.classList.contains("is-auto-hidden") &&
       h && n && h.top>=-1 && h.top<=1 && n.top>=h.bottom-1;
   }""")
   home.keyboard.press("Escape")
   home.wait_for_function("!document.querySelector('.primary-nav').classList.contains('is-open')")
   home.evaluate("document.activeElement?.blur(); window.TokiMotion.setHeaderVisible(false)")
   home.wait_for_function("document.querySelector('.site-header').classList.contains('is-auto-hidden')")
   home.evaluate("""() => {
     const hero=document.querySelector(".hero-opening");
     const scroller=document.scrollingElement;
     scroller.style.setProperty("scroll-behavior","auto","important");
     scroller.scrollTop=Math.max(0,window.scrollY+hero.getBoundingClientRect().bottom+80);
   }""")
   home.wait_for_timeout(120)
   assert home.locator(".hero-opening").evaluate("(node)=>node.getBoundingClientRect().bottom<0"), "Hero must clear the viewport before opening the mobile menu"
   # Reveal the masthead through a real upward scroll after the hero clears.
   home.evaluate("""() => {
     const scroller=document.scrollingElement;
     scroller.scrollTop=Math.max(0,scroller.scrollTop-12);
   }""")
   home.wait_for_function("""() => {
     const header=document.querySelector(".site-header");
     const bounds=header?.getBoundingClientRect();
     return header && bounds && bounds.top>=-1 && bounds.top<=1 &&
       !header.classList.contains("is-auto-hidden") &&
       header.getAttribute("aria-hidden")==="false" && !header.inert &&
       !header.getAnimations().some(animation=>animation.playState==="running");
   }""")
   header_box=home.locator(".site-header").bounding_box()
   assert header_box and -1<=header_box["y"]<=1, f"Header did not reveal after hero exit: {header_box}"
   menu=home.locator(".menu-toggle");menu.click()
   home.wait_for_function("""() => {
     const header=document.querySelector(".site-header");
     const nav=document.querySelector(".primary-nav");
     return header && nav && nav.classList.contains("is-open") &&
       getComputedStyle(nav).display!=="none" &&
       document.querySelector(".menu-toggle")?.getAttribute("aria-expanded")==="true";
   }""")
   drawer=home.locator(".primary-nav")
   # The shared motion helper cancels finished WAAPI animations, so wait for
   # the panel and its staggered links to settle instead of sampling mid-entry.
   home.wait_for_function("""() => {
     const nav=document.querySelector(".primary-nav");
     if(!nav) return false;
     const animations=[
       ...nav.getAnimations(),
       ...Array.from(nav.querySelectorAll("a")).flatMap(link=>link.getAnimations())
     ];
     return animations.every(animation=>animation.playState!=="running");
   }""")
   drawer_state=drawer.evaluate("""nav => {
     const header=document.querySelector(".site-header");
     const h=header.getBoundingClientRect(), n=nav.getBoundingClientRect();
     const first=nav.querySelector("a")?.getBoundingClientRect();
     const style=getComputedStyle(nav);
     return {
       position:style.position, overflowY:style.overflowY,
       top:n.top, bottom:n.bottom, left:n.left, right:n.right,
       headerBottom:h.bottom, headerLeft:h.left, headerRight:h.right,
       firstTop:first?.top, firstBottom:first?.bottom,
       scrollHeight:nav.scrollHeight, clientHeight:nav.clientHeight
     };
   }""")
   assert drawer_state["position"]=="absolute", f"Mobile drawer must be anchored to the header, got {drawer_state}"
   assert drawer_state["overflowY"] in ("auto","scroll"), f"Mobile drawer must scroll within its viewport, got {drawer_state}"
   assert drawer_state["top"]>=drawer_state["headerBottom"]-1, f"Mobile drawer overlaps the header after its entrance transition: {drawer_state}"
   assert drawer_state["left"]<=drawer_state["headerLeft"]+1 and drawer_state["right"]>=drawer_state["headerRight"]-1, f"Mobile drawer does not span the header: {drawer_state}"
   assert drawer_state["firstTop"]>=drawer_state["top"]-1 and drawer_state["firstBottom"]<=drawer_state["bottom"]+1, f"First navigation link is clipped: {drawer_state}"
   quick_cta_state=home.locator(".mobile-cta").evaluate("""element=>{
     const style=getComputedStyle(element);
     return {width:element.getBoundingClientRect().width,opacity:style.opacity,visibility:style.visibility,pointerEvents:style.pointerEvents};
   }""")
   assert quick_cta_state["width"]<=210, f"Mobile CTA should remain compact: {quick_cta_state}"
   assert quick_cta_state["opacity"]=="0" and quick_cta_state["visibility"]=="hidden" and quick_cta_state["pointerEvents"]=="none", f"Sticky controls must not overlap an open mobile drawer: {quick_cta_state}"
   icon_transform=home.locator(".menu-toggle span").first.evaluate("(el)=>getComputedStyle(el).transform")
   assert icon_transform != "none", "Mobile menu icon did not enter its open state"
   home.keyboard.press("Escape")
   assert menu.get_attribute("aria-expanded")=="false"
   home.wait_for_function("!document.querySelector('.primary-nav').classList.contains('is-open')")
   # A short phone viewport must keep the complete menu reachable through its own scroll region.
   home.set_viewport_size({"width":390,"height":280})
   menu.click()
   home.wait_for_function("""() => {
     const header=document.querySelector(".site-header");
     const nav=document.querySelector(".primary-nav");
     const h=header?.getBoundingClientRect(), n=nav?.getBoundingClientRect();
     return nav?.classList.contains("is-open") &&
       header?.getAttribute("aria-hidden")==="false" && !header.inert &&
       !header.classList.contains("is-auto-hidden") &&
       h && n && h.top>=-1 && h.top<=1 && n.top>=h.bottom-1;
   }""")
   home.wait_for_function("""() => {
     const nav=document.querySelector(".primary-nav");
     if(!nav) return false;
     const animations=[
       ...nav.getAnimations(),
       ...Array.from(nav.querySelectorAll("a")).flatMap(link=>link.getAnimations())
     ];
     return animations.every(animation=>animation.playState!=="running");
   }""")
   link_metrics=drawer.evaluate("""nav=>{
     const style=getComputedStyle(nav);
     const links=Array.from(nav.querySelectorAll("a"));
     return {
       count:links.length,
       heights:links.map(a=>a.getBoundingClientRect().height),
       tops:links.map(a=>a.getBoundingClientRect().top),
       linkStyles:links.map(a=>({className:a.className,position:getComputedStyle(a).position,top:getComputedStyle(a).top,transform:getComputedStyle(a).transform,translate:getComputedStyle(a).translate,display:getComputedStyle(a).display,flex:getComputedStyle(a).flex,margin:getComputedStyle(a).margin,offsetTop:a.offsetTop,offsetHeight:a.offsetHeight,offsetParent:a.offsetParent?.tagName,parent:a.parentElement?.tagName,animations:a.getAnimations().map(x=>({state:x.playState,time:x.currentTime}))})),
       navBox:(()=>{const r=nav.getBoundingClientRect();return {top:r.top,bottom:r.bottom,transform:style.transform,scrollTop:nav.scrollTop,scrollHeight:nav.scrollHeight,clientHeight:nav.clientHeight}})(),
       headerBox:(()=>{const h=document.querySelector(".site-header"),r=h.getBoundingClientRect(),s=getComputedStyle(h);return {top:r.top,bottom:r.bottom,transform:s.transform,className:h.className,ariaHidden:h.getAttribute("aria-hidden"),inert:h.inert}})(),
       overflowY:style.overflowY,
       flexDirection:style.flexDirection,
       justifyContent:style.justifyContent
     };
   }""")
   assert link_metrics["count"]==7, f"Mobile navigation must retain all seven destinations: {link_metrics}"
   assert link_metrics["flexDirection"]=="column", f"Mobile navigation must stack links vertically: {link_metrics}"
   assert link_metrics["justifyContent"]=="flex-start", f"Mobile navigation must start at the top edge, not distribute overflow above the drawer: {link_metrics}"
   assert link_metrics["tops"][0]>=drawer.evaluate("nav=>nav.getBoundingClientRect().top")-1, f"First mobile link begins above the drawer: {link_metrics}"
   assert all(height>=48 for height in link_metrics["heights"]), f"Mobile navigation links must retain 48px touch targets: {link_metrics}"
   assert all(link_metrics["tops"][i+1]>=link_metrics["tops"][i]+link_metrics["heights"][i]-1 for i in range(6)), f"Mobile navigation links overlap or are out of vertical order: {link_metrics}"
   assert link_metrics["overflowY"] in ("auto","scroll"), f"Short-screen menu is not scrollable: {link_metrics}"
   short_state=drawer.evaluate("nav=>({overflowY:getComputedStyle(nav).overflowY,scrollHeight:nav.scrollHeight,clientHeight:nav.clientHeight,maxHeight:getComputedStyle(nav).maxHeight})")
   assert short_state["overflowY"] in ("auto","scroll"), f"Short mobile drawer must own its scroll region: {short_state}"
   assert short_state["scrollHeight"]>short_state["clientHeight"], f"Short mobile viewport must cause natural drawer overflow: {short_state}; link_metrics={link_metrics}"
   last_link=drawer.locator("a").last
   last_link.scroll_into_view_if_needed()
   assert last_link.is_visible(), "Last navigation link is not reachable inside a short mobile drawer"
   assert drawer.evaluate("nav=>nav.scrollTop>0"), "Navigation scroll did not stay inside the drawer"
   home.keyboard.press("Escape")
   home.wait_for_function("!document.querySelector('.primary-nav').classList.contains('is-open')")
   menu.click()
   home.wait_for_function("document.querySelector('.primary-nav').classList.contains('is-open')")
   assert drawer.evaluate("nav=>nav.scrollTop===0"), "Reopened mobile navigation must reset to the first item"

   home.keyboard.press("Escape")
   home.wait_for_function("!document.querySelector('.primary-nav').classList.contains('is-open')")
   menu.click()
   home.evaluate("document.querySelector('.hero-opening').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
   assert menu.get_attribute("aria-expanded")=="false","Outside click did not close mobile navigation"
   home.wait_for_function("!document.querySelector('.primary-nav').classList.contains('is-open')")
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
   # Shared-element View Transitions commit the dialog update on the next frame.
   archive.wait_for_function(
    "() => { const dialog = document.querySelector('#album-dialog'); return dialog?.open && getComputedStyle(dialog).display !== 'none'; }",
    timeout=1500
   )
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
   # The archive is an interior page: return to the top and let the production
   # scroll controller reveal the masthead naturally before testing the hit target.
   archive.evaluate("""() => {
       const scroller = document.scrollingElement;
       scroller.style.setProperty("scroll-behavior", "auto", "important");
       scroller.scrollTop = 0;
   }""")
   archive.wait_for_function("""() => {
       const header = document.querySelector(".site-header");
       return window.scrollY <= 1 && header &&
           !header.classList.contains("is-auto-hidden") &&
           !header.classList.contains("is-initial-hidden") &&
           header.getAttribute("aria-hidden") === "false" && !header.inert &&
           !header.getAnimations().some(animation => animation.playState === "running");
   }""")
   menu_hit=archive.locator(".menu-toggle").evaluate("""button => {
       const rect=button.getBoundingClientRect();
       const target=document.elementFromPoint(rect.left+rect.width/2,rect.top+rect.height/2);
       return {accepted:target===button||button.contains(target),target:target?.className||target?.tagName};
   }""")
   assert menu_hit["accepted"], f"Archive masthead is occluded by {menu_hit['target']}"
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
