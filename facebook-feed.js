(function(){
"use strict";
const list=document.querySelector("#facebook-feed-list"),status=document.querySelector("#facebook-feed-status");
if(!list||!status)return;
const PAGE="https://www.facebook.com/tokisatsuiephotography/";
let sdkPromise=null;
function el(tag,cls,txt){const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=String(txt);return n;}
function validUrl(value){
 try{
  const u=new URL(String(value||"").trim()),host=u.hostname.toLowerCase(),p=u.pathname.toLowerCase();
  if(u.protocol!=="https:"||!["facebook.com","www.facebook.com","m.facebook.com","web.facebook.com"].includes(host))return "";
  if(!(/\/(posts|permalink|videos|reel|photo|watch|share\/p|share\/r)(\/|$)/.test(p)||p.endsWith("/photo.php")||u.searchParams.has("story_fbid")||u.searchParams.has("fbid")||u.searchParams.has("v")))return "";
  u.hash="";return u.href;
 }catch(e){return "";}
}
function showEmpty(){
 const state=el("div","facebook-feed-state");
 state.append(el("span","facebook-state-mark","時"),el("strong","","No selected posts yet."),el("p","","Add a public post URL to the curated collection. New selections will appear here after the update is published."));
 const link=el("a","facebook-state-link","OPEN THE FEED MANAGER ↗");link.href="./feed-manager.html";state.append(link);
 list.replaceChildren(state);list.setAttribute("aria-busy","false");
}
function loadSDK(){
 if(window.FB&&window.FB.XFBML)return Promise.resolve(window.FB);
 if(sdkPromise)return sdkPromise;
 sdkPromise=new Promise(function(resolve,reject){
  let script=document.getElementById("facebook-jssdk");
  if(!script){script=document.createElement("script");script.id="facebook-jssdk";script.async=true;script.defer=true;script.crossOrigin="anonymous";script.src="https://connect.facebook.net/en_US/sdk.js#xfbml=0&version=v27.0";document.head.append(script);}
  script.addEventListener("load",function(){if(window.FB&&window.FB.XFBML)resolve(window.FB);else reject(new Error("Facebook embed SDK did not initialize."));},{once:true});
  script.addEventListener("error",function(){reject(new Error("Facebook embed SDK was blocked."));},{once:true});
 });
 return sdkPromise;
}
function render(posts){
 list.replaceChildren();const entries=[];
 posts.forEach(function(post,index){
  const card=el("article","facebook-embed-card"),head=el("div","facebook-embed-heading");
  head.append(el("span","facebook-embed-index",String(index+1).padStart(2,"0")),el("span","facebook-embed-label",post.label||"FROM THE TOKI SATSUEI PAGE"));
  const open=el("a","facebook-embed-open","OPEN POST ↗");open.href=post.url;open.target="_blank";open.rel="noopener noreferrer";open.referrerPolicy="no-referrer";head.append(open);
  const plugin=el("div","fb-post");plugin.setAttribute("data-href",post.url);plugin.setAttribute("data-show-text","true");plugin.setAttribute("data-lazy","true");
  const note=el("p","facebook-embed-note","Loading the original Facebook post…");
  card.append(head,plugin,note);list.append(card);entries.push({plugin,note});
 });
 list.setAttribute("aria-busy","false");
 loadSDK().then(function(FB){
  if(typeof FB.init==="function")FB.init({xfbml:false,version:"v27.0"});
  FB.XFBML.parse(list);
  window.setTimeout(function(){entries.forEach(function(x){
   if(x.plugin.querySelector("iframe")){x.note.textContent="Embedded directly from Facebook. Use the controls inside the post to react or comment.";x.note.classList.add("is-embedded");}
   else{x.note.textContent="Facebook could not display this post here. Open the original post above; it may be private, removed, or restricted.";x.note.classList.add("is-unavailable");}
  });},6500);
 }).catch(function(){entries.forEach(function(x){x.note.textContent="Facebook's embed was blocked or unavailable. Open the original post above.";x.note.classList.add("is-unavailable");});});
}
fetch("./facebook-posts.json?v="+Date.now(),{cache:"no-store",headers:{Accept:"application/json"}})
.then(function(r){if(!r.ok)throw new Error("Post list unavailable.");return r.json();})
.then(function(config){
 const seen=new Set(),posts=(Array.isArray(config.posts)?config.posts:[]).map(function(item){
  const url=validUrl(typeof item==="string"?item:item&&item.url);if(!url||seen.has(url))return null;seen.add(url);
  return {url:url,label:typeof item==="object"&&item&&typeof item.label==="string"?item.label.trim().slice(0,90):""};
 }).filter(Boolean).slice(0,12);
 status.textContent=posts.length?"SELECTED FACEBOOK POSTS · "+posts.length+" "+(posts.length===1?"POST":"POSTS"):"THE COLLECTION IS READY FOR ITS FIRST POST";
 if(posts.length)render(posts);else showEmpty();
})
.catch(function(){
 status.textContent="POST COLLECTION COULD NOT LOAD";
 const state=el("div","facebook-feed-state");state.append(el("span","facebook-state-mark","時"),el("strong","","We couldn't load the selected posts."),el("p","","Reload the page or open our Facebook Page directly."));
 const link=el("a","facebook-state-link","OPEN FACEBOOK PAGE ↗");link.href=PAGE;link.target="_blank";link.rel="noopener noreferrer";state.append(link);
 list.replaceChildren(state);list.setAttribute("aria-busy","false");
});
})();