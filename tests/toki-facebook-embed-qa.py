#!/usr/bin/env python3
"""Browser QA for curated Facebook embeds and expanded manager features."""
from __future__ import annotations
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
P1="https://www.facebook.com/tokisatsuiephotography/posts/123456789"
P2="https://www.facebook.com/tokisatsuiephotography/reel/987654321"
SAMPLE={"schema_version":2,"posts":[{"url":P1,"label":"LATEST FRAME","category":"cosplay","featured":True},{"url":P2,"label":"EVENT RECAP","category":"events","featured":False}]}
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**k):super().__init__(*a,directory=str(ROOT),**k)
 def log_message(self,*a):pass
def main():
 server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler));thread=Thread(target=server.serve_forever,daemon=True);thread.start();base="http://127.0.0.1:"+str(server.server_port);errors=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"]);context=browser.new_context(viewport={"width":1440,"height":900})
   context.route("https://fonts.googleapis.com/**",lambda r:r.abort());context.route("https://fonts.gstatic.com/**",lambda r:r.abort())
   context.route("**/facebook-posts.json**",lambda r:r.fulfill(status=200,content_type="application/json",body=json.dumps(SAMPLE)))
   def sdk(route):route.fulfill(status=200,content_type="application/javascript",body="""window.__fbParseCount=0;window.FB={init:function(){},XFBML:{parse:function(root){window.__fbParseCount+=root.querySelectorAll('.fb-post').length;root.querySelectorAll('.fb-post').forEach(function(n){var f=document.createElement('iframe');f.title='Mock public Facebook post';n.appendChild(f);});}}};""")
   context.route("https://connect.facebook.net/**",sdk)
   page=context.new_page();page.on("pageerror",lambda e:errors.append(str(e)));page.goto(base+"/index.html",wait_until="domcontentloaded")
   page.locator(".facebook-embed-card iframe").first.wait_for(state="attached",timeout=7000);cards=page.locator(".facebook-embed-card")
   assert cards.count()==2 and cards.nth(0).locator(".facebook-embed-category").inner_text()=="Cosplay"
   assert "is-featured" in cards.nth(0).get_attribute("class");assert page.evaluate("window.__fbParseCount")==2
   page.locator("#facebook-feed-search").fill("event");assert page.locator(".facebook-embed-card").count()==1
   page.locator("#facebook-feed-search").fill("");page.locator(".facebook-feed-filter").filter(has_text="Cosplay").click();assert page.locator(".facebook-embed-card").count()==1
   page.locator(".facebook-feed-filter").filter(has_text="All").click()
   checks=0
   for width in [1440,1024,820,680,430,390,360,320]:
    page.set_viewport_size({"width":width,"height":850});s=page.evaluate("""()=>({doc:document.documentElement.scrollWidth,col:document.querySelector('.facebook-feed-column').getBoundingClientRect().width,rights:[...document.querySelectorAll('.facebook-embed-card')].map(x=>x.getBoundingClientRect().right)})""")
    assert s["doc"]<=width+1 and s["col"]>0 and all(x<=width+1 for x in s["rights"]);checks+=1
   manager=context.new_page();manager.on("pageerror",lambda e:errors.append(str(e)));manager.route("**/facebook-posts.json**",lambda r:r.fulfill(status=200,content_type="application/json",body=json.dumps(SAMPLE)));manager.goto(base+"/feed-manager.html",wait_until="domcontentloaded")
   manager.locator(".manager-post-row").nth(1).wait_for(state="visible",timeout=6000);assert manager.locator(".manager-post-row").count()==2
   manager.locator("#manager-search").fill("event");assert manager.locator(".manager-post-row").count()==1;manager.locator("#manager-search").fill("")
   manager.locator("#manager-url").fill("https://www.facebook.com/tokisatsuiephotography/posts/555555555");manager.locator("#manager-label").fill("Foundation Day");manager.locator("#manager-category").select_option("events");manager.locator("#manager-featured").check();manager.locator("#manager-add-form button[type=submit]").click();assert manager.locator(".manager-post-row").count()==3
   manager.locator("#manager-bulk-input").fill("https://www.facebook.com/tokisatsuiephotography/posts/666666666\nhttps://www.facebook.com/tokisatsuiephotography/posts/777777777");manager.locator("#manager-bulk-add").click();assert manager.locator(".manager-post-row").count()==5
   manager.locator("#manager-filter").select_option("events");assert manager.locator(".manager-post-row").count()==2;manager.locator("#manager-filter").select_option("all")
   manager.locator(".manager-post-controls button[aria-label='Preview Facebook post']").first.click();assert manager.locator("#manager-preview-dialog[open]").count()==1;manager.locator("#manager-preview-close").click()
   manager.locator("#manager-copy").click();assert '"schema_version": 2' in manager.locator("#manager-json").input_value()
   manager.locator("#manager-import-json").fill(json.dumps(SAMPLE));manager.locator("#manager-import").click();assert manager.locator(".manager-post-row").count()==2
   manager.locator("#manager-url").fill("https://example.com/not-facebook");manager.locator("#manager-add-form button[type=submit]").click();assert not manager.locator("#manager-error").is_hidden()
   assert not errors,"JavaScript errors: "+"; ".join(errors);browser.close()
  print("PASS TOKI SATSUEI feature QA: embed metadata, search, category filters, 8 responsive widths, add/bulk import, featured posts, preview, JSON import/export.")
 finally:server.shutdown();server.server_close();thread.join(timeout=2)
if __name__=="__main__":main()
