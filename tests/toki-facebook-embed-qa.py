#!/usr/bin/env python3
"""Browser QA for curated individual Facebook post embeds and the feed manager."""
from __future__ import annotations
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
P1="https://www.facebook.com/tokisatsuiephotography/posts/123456789"
P2="https://www.facebook.com/tokisatsuiephotography/posts/987654321"
SAMPLE={"schema_version":1,"posts":[{"url":P1,"label":"LATEST FRAME"},{"url":P2,"label":""}]}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def log_message(self,*args):pass

def main():
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler));thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    base="http://127.0.0.1:"+str(server.server_port);errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
            context=browser.new_context(viewport={"width":1440,"height":900})
            context.route("https://fonts.googleapis.com/**",lambda r:r.abort())
            context.route("https://fonts.gstatic.com/**",lambda r:r.abort())
            context.route("**/facebook-posts.json**",lambda r:r.fulfill(status=200,content_type="application/json",body=json.dumps(SAMPLE)))
            def sdk(route):
                route.fulfill(status=200,content_type="application/javascript",body="""
window.__fbParseCount=0;
window.FB={init:function(){},XFBML:{parse:function(root){
window.__fbParseCount+=root.querySelectorAll('.fb-post').length;
root.querySelectorAll('.fb-post').forEach(function(n){var f=document.createElement('iframe');f.title='Mock Facebook public post';n.appendChild(f);});
}}};
""")
            context.route("https://connect.facebook.net/**",sdk)
            page=context.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(base+"/index.html",wait_until="domcontentloaded")
            page.locator(".facebook-embed-card iframe").first.wait_for(state="attached",timeout=7000)
            cards=page.locator(".facebook-embed-card")
            assert cards.count()==2
            assert cards.nth(0).locator(".facebook-embed-label").inner_text()=="LATEST FRAME"
            assert cards.nth(0).locator(".fb-post").get_attribute("data-href")==P1
            assert cards.nth(0).locator(".fb-post").get_attribute("data-show-text")=="true"
            assert cards.nth(0).locator(".facebook-embed-open").get_attribute("href")==P1
            assert page.evaluate("window.__fbParseCount")==2
            assert page.locator("#facebook-page-embed").count()==0
            assert "SELECTED FACEBOOK POSTS" in page.locator("#facebook-feed-status").inner_text()
            checks=0
            for width in [1440,1024,820,680,430,390,360,320]:
                page.set_viewport_size({"width":width,"height":850})
                state=page.evaluate("""()=>({doc:document.documentElement.scrollWidth,col:document.querySelector('.facebook-feed-column').getBoundingClientRect().width,rights:[...document.querySelectorAll('.facebook-embed-card')].map(x=>x.getBoundingClientRect().right)})""")
                assert state["doc"]<=width+1,"Page overflow at "+str(width)
                assert state["col"]>0
                assert all(x<=width+1 for x in state["rights"])
                checks+=1
            manager=context.new_page()
            manager.route("**/facebook-posts.json**",lambda r:r.fulfill(status=200,content_type="application/json",body=json.dumps(SAMPLE)))
            manager.goto(base+"/feed-manager.html",wait_until="domcontentloaded")
            manager.locator(".manager-post-row").nth(1).wait_for(state="visible",timeout=5000)
            assert manager.locator(".manager-post-row").count()==2
            manager.locator("#manager-url").fill("https://www.facebook.com/tokisatsuiephotography/posts/555555555")
            manager.locator("#manager-add-form button[type=submit]").click()
            assert manager.locator(".manager-post-row").count()==3
            manager.locator(".manager-post-controls button[aria-label='Move post up']").nth(1).click()
            exported=json.loads(manager.locator("#manager-json").input_value())
            assert exported["posts"][1]["url"].endswith("/555555555")
            manager.locator("#manager-url").fill("https://example.com/not-facebook")
            manager.locator("#manager-add-form button[type=submit]").click()
            assert not manager.locator("#manager-error").is_hidden()
            assert manager.locator("#manager-github").get_attribute("href").endswith("/edit/main/facebook-posts.json")
            assert not errors,"JavaScript errors: "+"; ".join(errors)
            browser.close()
        print("PASS TOKI SATSUEI curated Facebook QA: embeds, SDK parsing, 8 responsive widths, manager add/reorder/export, and unsafe-link rejection.")
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
if __name__=="__main__":main()
