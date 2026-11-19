(() => {
  "use strict";

const menuButton=document.querySelector(".menu-toggle");
const nav=document.querySelector(".primary-nav");
const siteHeader=document.querySelector(".site-header");
const progressBar=document.querySelector("#page-progress-bar");
const backToTop=document.querySelector("#back-to-top");
const form=document.querySelector("#inquiry-form");
const status=document.querySelector("#form-status");
const reduceMotionQuery=window.matchMedia("(prefers-reduced-motion: reduce)");
const hoverPointer=window.matchMedia("(hover: hover) and (pointer: fine)").matches;
let reducedMotion=reduceMotionQuery.matches;

function setMenuOpen(open,returnFocus=false){
  if(!menuButton||!nav)return;
  if(window.TokiMotion?.setMenuOpen)window.TokiMotion.setMenuOpen(menuButton,nav,open);
  else{
    nav.classList.toggle("is-open",open);
    menuButton.setAttribute("aria-expanded",String(open));
    menuButton.setAttribute("aria-label",open?"Close navigation":"Open navigation");
  }
  if(open)setHeaderHidden(false);
  if(!open&&returnFocus)menuButton.focus();
}
if(menuButton&&nav){
  menuButton.addEventListener("click",()=>setMenuOpen(menuButton.getAttribute("aria-expanded")!=="true"));
  nav.querySelectorAll("a").forEach(link=>link.addEventListener("click",()=>setMenuOpen(false)));
  document.addEventListener("click",event=>{
    if(nav.classList.contains("is-open")&&!siteHeader?.contains(event.target))setMenuOpen(false);
  });
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"&&nav.classList.contains("is-open")){event.preventDefault();setMenuOpen(false,true);}
  });
  window.matchMedia("(min-width: 821px)").addEventListener?.("change",event=>{if(event.matches)setMenuOpen(false);});
}

let scrollTicking=false,lastScrollY=window.scrollY,lastScrollDirection="up",hoverRevealed=false;
function setHeaderHidden(hidden){
  if(!siteHeader)return;
  const shouldHide=Boolean(hidden)&&window.scrollY>64&&!nav?.classList.contains("is-open")&&!siteHeader.matches(":focus-within");
  siteHeader.classList.toggle("is-auto-hidden",shouldHide);
}
function updatePageChrome(){
  const root=document.documentElement,currentY=window.scrollY,delta=currentY-lastScrollY;
  if(currentY<=36){lastScrollDirection="up";hoverRevealed=false;setHeaderHidden(false);}
  else if(delta>1){lastScrollDirection="down";hoverRevealed=false;setHeaderHidden(true);}
  else if(delta< -1){lastScrollDirection="up";hoverRevealed=false;setHeaderHidden(false);}
  if(nav?.classList.contains("is-open")||siteHeader?.matches(":focus-within"))setHeaderHidden(false);
  lastScrollY=currentY;
  const progress=Math.min(1,Math.max(0,currentY/Math.max(1,root.scrollHeight-window.innerHeight)));
  if(progressBar)progressBar.style.transform="scaleX("+progress+")";
  siteHeader?.classList.toggle("is-scrolled",currentY>28);
  backToTop?.classList.toggle("is-visible",currentY>520);
  scrollTicking=false;
}
window.addEventListener("scroll",()=>{if(!scrollTicking){requestAnimationFrame(updatePageChrome);scrollTicking=true;}},{passive:true});
window.addEventListener("resize",updatePageChrome,{passive:true});
window.addEventListener("orientationchange",()=>requestAnimationFrame(updatePageChrome),{passive:true});
if(siteHeader){
  window.addEventListener("pointermove",event=>{
    if(!hoverPointer||event.pointerType==="touch")return;
    if(event.clientY<=40){hoverRevealed=true;setHeaderHidden(false);return;}
    if(hoverRevealed&&event.clientY>siteHeader.offsetHeight+14){
      hoverRevealed=false;
      if(lastScrollDirection==="down"&&window.scrollY>64)setHeaderHidden(true);
    }
  },{passive:true});
  siteHeader.addEventListener("focusin",()=>{hoverRevealed=false;setHeaderHidden(false);});
}
updatePageChrome();
backToTop?.addEventListener("click",()=>window.scrollTo({top:0,behavior:reducedMotion?"auto":"smooth"}));

const hero=document.querySelector(".hero-opening"),heroPhoto=hero?.querySelector(".hero-photo");
if(hero&&heroPhoto&&hoverPointer&&!reducedMotion){
  let pointerFrame=0,pointerX=0,pointerY=0;
  hero.addEventListener("pointermove",event=>{
    if(event.pointerType==="touch")return;
    const rect=hero.getBoundingClientRect();
    pointerX=((event.clientX-rect.left)/Math.max(1,rect.width)-.5)*-12;
    pointerY=((event.clientY-rect.top)/Math.max(1,rect.height)-.5)*-9;
    if(!pointerFrame)pointerFrame=requestAnimationFrame(()=>{
      heroPhoto.style.setProperty("--hero-pan-x",pointerX.toFixed(1)+"px");
      heroPhoto.style.setProperty("--hero-pan-y",pointerY.toFixed(1)+"px");
      const pointerRect=hero.getBoundingClientRect();
      hero.style.setProperty("--hero-pointer-x",(((event.clientX-pointerRect.left)/Math.max(1,pointerRect.width))*100).toFixed(1)+"%");
      hero.style.setProperty("--hero-pointer-y",(((event.clientY-pointerRect.top)/Math.max(1,pointerRect.height))*100).toFixed(1)+"%");
      pointerFrame=0;
    });
  });
  hero.addEventListener("pointerleave",()=>{
    heroPhoto.style.setProperty("--hero-pan-x","0px");
    heroPhoto.style.setProperty("--hero-pan-y","0px");
    hero.style.setProperty("--hero-pointer-x","72%");
    hero.style.setProperty("--hero-pointer-y","42%");
  });
}

const revealTargets=document.querySelectorAll("[data-reveal]");
let revealObserver=null;
function showAllReveals(){revealTargets.forEach(target=>target.classList.add("is-visible"));}
if(revealTargets.length){
  document.documentElement.classList.add("motion-ready");
  if(reducedMotion||!("IntersectionObserver" in window))showAllReveals();
  else{
    revealObserver=new IntersectionObserver(entries=>entries.forEach(entry=>{
      if(entry.isIntersecting){entry.target.classList.add("is-visible");revealObserver.unobserve(entry.target);}
    }),{threshold:.12,rootMargin:"0px 0px -6% 0px"});
    revealTargets.forEach(target=>revealObserver.observe(target));
  }
}
reduceMotionQuery.addEventListener?.("change",event=>{
  reducedMotion=event.matches;
  if(reducedMotion){showAllReveals();heroPhoto?.style.removeProperty("--hero-pan-x");heroPhoto?.style.removeProperty("--hero-pan-y");}
});

const navLinks=[...document.querySelectorAll('.primary-nav a[href^="#"]')];
const sections=navLinks.map(link=>document.querySelector(link.getAttribute("href"))).filter(Boolean);
if("IntersectionObserver" in window&&sections.length){
  const sectionObserver=new IntersectionObserver(entries=>entries.forEach(entry=>{
    if(entry.isIntersecting)navLinks.forEach(link=>{
      if(link.getAttribute("href")==="#"+entry.target.id)link.setAttribute("aria-current","location");
      else link.removeAttribute("aria-current");
    });
  }),{rootMargin:"-24% 0px -65% 0px"});
  sections.forEach(section=>sectionObserver.observe(section));
}

let galleryFilterRevision=0;
const galleryCards=[...document.querySelectorAll(".gallery-card")];
document.querySelectorAll(".filter-button").forEach(button=>button.addEventListener("click",()=>{
  const filter=button.dataset.filter,revision=++galleryFilterRevision;
  document.querySelectorAll(".filter-button").forEach(item=>{
    const active=item===button;item.classList.toggle("is-active",active);item.setAttribute("aria-pressed",String(active));
  });
  galleryCards.forEach(card=>{
    card.getAnimations?.().forEach(animation=>animation.cancel());
    const visible=filter==="all"||card.dataset.category===filter;
    if(visible){
      const wasHidden=card.hidden;card.hidden=false;
      if(wasHidden&&!reducedMotion&&card.animate)card.animate([{opacity:0,transform:"translateY(9px)"},{opacity:1,transform:"translateY(0)"}],{duration:240,easing:"cubic-bezier(.2,.7,.2,1)"});
    }else if(!reducedMotion&&card.animate){
      const fade=card.animate([{opacity:1,transform:"translateY(0)"},{opacity:0,transform:"translateY(8px)"}],{duration:150,easing:"ease-in"});
      fade.finished.then(()=>{if(revision===galleryFilterRevision&&filter!=="all"&&card.dataset.category!==filter)card.hidden=true;}).catch(()=>{});
    }else card.hidden=true;
  });
}));

const lightbox=document.querySelector("#lightbox");
const lightboxImage=document.querySelector(".lightbox-image");
const lightboxTitle=document.querySelector(".lightbox-caption strong");
const lightboxCaption=document.querySelector(".lightbox-caption span");
const lightboxPosition=document.querySelector(".lightbox-position");
const lightboxPrevious=document.querySelector(".lightbox-prev");
const lightboxNext=document.querySelector(".lightbox-next");
const visibleGalleryCards=()=>galleryCards.filter(card=>!card.hidden);
let lightboxCards=[],lightboxIndex=0,touchStartX=0,touchStartY=0;
function renderLightboxFrame(){
  const card=lightboxCards[lightboxIndex];if(!card)return;
  const updateImage=()=>{
    lightboxImage.src=card.dataset.full;
    lightboxImage.alt=card.querySelector("img")?.alt||card.dataset.title||"TOKI SATSUEI photograph";
  };
  if(lightboxImage.getAttribute("src")&&window.TokiMotion?.swap){
    window.TokiMotion.swap(lightboxImage,updateImage,{duration:110,enterDuration:230});
  }else updateImage();
  lightboxTitle.textContent=card.dataset.title||"";
  lightboxCaption.textContent=card.dataset.caption||"";
  lightboxPosition.textContent=String(lightboxIndex+1).padStart(2,"0")+" / "+String(lightboxCards.length).padStart(2,"0");
  const multiple=lightboxCards.length>1;
  lightboxPrevious.disabled=!multiple;lightboxNext.disabled=!multiple;
}
function openLightbox(card){
  lightboxCards=visibleGalleryCards();
  lightboxIndex=Math.max(0,lightboxCards.indexOf(card));
  renderLightboxFrame();
  if(!lightbox.open)lightbox.showModal();
}
function stepLightbox(direction){
  if(!lightbox.open||lightboxCards.length<2)return;
  lightboxIndex=(lightboxIndex+direction+lightboxCards.length)%lightboxCards.length;
  renderLightboxFrame();
}
galleryCards.forEach(card=>card.addEventListener("click",()=>openLightbox(card)));
lightboxPrevious?.addEventListener("click",()=>stepLightbox(-1));
lightboxNext?.addEventListener("click",()=>stepLightbox(1));
function closeLightbox(){
  if(!lightbox?.open)return;
  if(window.TokiMotion?.closeDialog)window.TokiMotion.closeDialog(lightbox);
  else lightbox.close();
}
document.querySelector(".lightbox-close")?.addEventListener("click",closeLightbox);
lightbox?.addEventListener("click",event=>{if(event.target===lightbox)closeLightbox();});
lightbox?.addEventListener("cancel",event=>{event.preventDefault();closeLightbox();});
lightbox?.addEventListener("touchstart",event=>{
  const touch=event.changedTouches?.[0];if(!touch)return;
  touchStartX=touch.clientX;touchStartY=touch.clientY;
},{passive:true});
lightbox?.addEventListener("touchend",event=>{
  const touch=event.changedTouches?.[0];if(!touch)return;
  const dx=touch.clientX-touchStartX,dy=touch.clientY-touchStartY;
  if(Math.abs(dx)>44&&Math.abs(dx)>Math.abs(dy)*1.2)stepLightbox(dx<0?1:-1);
},{passive:true});
lightbox?.addEventListener("close",()=>{lightboxImage?.removeAttribute("src");lightboxCards=[];lightboxIndex=0;});
document.addEventListener("keydown",event=>{
  if(!lightbox?.open)return;
  if(event.key==="ArrowRight"){event.preventDefault();stepLightbox(1);}
  else if(event.key==="ArrowLeft"){event.preventDefault();stepLightbox(-1);}
});

const sessionSelect=form?.querySelector('select[name="session"]');
const sessionDurationNote=form?.querySelector("#session-duration-note");
const sessionCards=[...document.querySelectorAll(".package-card[data-session]")];
function updateSessionDurationNote(){
  if(!sessionSelect||!sessionDurationNote)return;
  const selected=sessionSelect.selectedOptions?.[0];
  if(!selected?.value){
    sessionDurationNote.textContent="Choose a session to see its expected duration.";
    return;
  }
  const duration=selected.dataset.duration||"Agreed before confirmation";
  sessionDurationNote.textContent=duration==="Agreed before confirmation"
    ?"Duration will be agreed with you in writing before the session is confirmed."
    :"Typical duration: "+duration+". The exact start and end time will be agreed in writing.";
}
sessionSelect?.addEventListener("change",updateSessionDurationNote);
updateSessionDurationNote();
function selectSession(card,{moveToForm=true}={}) {
  if(!card||!sessionSelect)return;
  sessionCards.forEach(item=>{
    const selected=item===card;
    item.classList.toggle("is-selected",selected);
    item.querySelector(".package-link")?.setAttribute("aria-pressed",String(selected));
  });
  sessionSelect.value=card.dataset.session;
  sessionSelect.dispatchEvent(new Event("change",{bubbles:true}));
  if(status){
    const message="Selected "+(card.dataset.sessionTitle||"session")+". Add your preferred date and shoot details below.";
    if(window.TokiMotion?.updateText)window.TokiMotion.updateText(status,message);
    else status.textContent=message;
  }
  form?.classList.add("is-prefilled");
  window.setTimeout(()=>form?.classList.remove("is-prefilled"),1100);
  if(moveToForm&&form){
    form.scrollIntoView({behavior:reducedMotion?"auto":"smooth",block:"center"});
    sessionSelect.focus({preventScroll:true});
  }
}
sessionCards.forEach(card=>{
  if(hoverPointer){
    card.addEventListener("pointermove",event=>{
      if(event.pointerType==="touch")return;
      const rect=card.getBoundingClientRect();
      card.style.setProperty("--card-pointer-x",((event.clientX-rect.left)/Math.max(1,rect.width)*100).toFixed(1)+"%");
      card.style.setProperty("--card-pointer-y",((event.clientY-rect.top)/Math.max(1,rect.height)*100).toFixed(1)+"%");
    },{passive:true});
    card.addEventListener("pointerleave",()=>{
      card.style.setProperty("--card-pointer-x","50%");
      card.style.setProperty("--card-pointer-y","10%");
    },{passive:true});
  }
  // Keyboard and screen-reader users operate the real button; pointer users can click anywhere on the card.
  card.querySelector(".package-link")?.addEventListener("click",()=>selectSession(card));
  card.addEventListener("click",event=>{
    if(event.target.closest("a,button,input,select,textarea"))return;
    selectSession(card);
  });
});

const TOKI_SUPABASE_URL="https://pjuwrngnrrvdiwqspkic.supabase.co";
const TOKI_SUPABASE_PUBLISHABLE_KEY="sb_publishable_PRGb0-smtTzCm9VHuM9NOQ_ZFh1wKRS";
const TOKI_BOOKING_ENDPOINT=TOKI_SUPABASE_URL+"/functions/v1/portfolio-submit";
const bookingButton=form?.querySelector(".form-submit");
const contactMethod=form?.querySelector("#contact-method");
const contactValue=form?.querySelector("#contact-value");
const preferredDate=form?.querySelector('input[name="preferred_date"]');
const preferredTime=form?.querySelector('input[name="preferred_time"]');
const alternateDate=form?.querySelector('input[name="alternate_date"]');
const submitLabel=bookingButton?.innerHTML||"Send booking request ↗";
const turnstileContainer=form?.querySelector("#toki-turnstile");
let turnstileWidgetId=null;
function handleTurnstileError(errorCode){
  updateBookingStatus(
    "Human verification is unavailable (Cloudflare code "+String(errorCode||"unknown")+"). Please reload or contact us through our official page.",
    "error"
  );
  return true;
}
function mountTurnstile(){
  if(!turnstileContainer||!window.turnstile?.render||turnstileWidgetId)return;
  const sitekey=turnstileContainer.dataset.sitekey||"";
  if(!sitekey)return;
  turnstileWidgetId=window.turnstile.render("#toki-turnstile",{
    sitekey,
    action:"toki_booking",
    theme:"light",
    size:"flexible",
    "error-callback":handleTurnstileError,
    "expired-callback":()=>updateBookingStatus("Human verification expired. Please complete the challenge again before submitting.","error"),
    "timeout-callback":()=>updateBookingStatus("Human verification timed out. Please complete the challenge again.","error")
  });
}
if(window.turnstile?.ready)window.turnstile.ready(mountTurnstile);
function readTurnstileToken(){
  if(!turnstileWidgetId||!window.turnstile?.getResponse)return "";
  return window.turnstile.getResponse(turnstileWidgetId)||"";
}
function resetTurnstile(){
  if(turnstileWidgetId&&window.turnstile?.reset)window.turnstile.reset(turnstileWidgetId);
}

function manilaNow(){
  const parts=new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Manila",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(new Date());
  const value=type=>parts.find(item=>item.type===type)?.value||"";
  return {date:value("year")+"-"+value("month")+"-"+value("day"),time:value("hour")+":"+value("minute")};
}
function nextMinute(time){
  const [hour,minute]=time.split(":").map(Number);
  const total=hour*60+minute+1;
  if(total>=1440)return "00:00";
  return String(Math.floor(total/60)).padStart(2,"0")+":"+String(total%60).padStart(2,"0");
}
function updateDateLimits(){
  const now=manilaNow();
  if(preferredDate)preferredDate.min=now.date;
  if(alternateDate)alternateDate.min=now.date;
  if(preferredTime){
    const sameDay=preferredDate?.value===now.date;
    const minimum=sameDay?nextMinute(now.time):"00:00";
    preferredTime.min=minimum;
    const noTimeLeft=sameDay&&minimum==="00:00";
    const tooEarly=sameDay&&preferredTime.value&&preferredTime.value<minimum;
    preferredTime.setCustomValidity(noTimeLeft?"No later time remains on this date. Choose a future date.":tooEarly?"Choose a time at least one minute in the future, using Philippine time.":"");
  }
  if(alternateDate)alternateDate.setCustomValidity(alternateDate.value&&preferredDate?.value===alternateDate.value?"Choose a different alternative date.":"");
}
function updateContactInput(){
  if(!contactMethod||!contactValue)return;
  const method=contactMethod.value;
  contactValue.type=method==="email"?"email":"text";
  contactValue.autocomplete=method==="email"?"email":"off";
  contactValue.inputMode=method==="email"?"email":"text";
  contactValue.placeholder=method==="instagram"?"Instagram username or profile link":method==="facebook"?"Facebook profile or Messenger contact":method==="email"?"Email address":"Choose a contact channel first";
  contactValue.setAttribute("aria-label",method==="email"?"Email address":method==="facebook"?"Facebook Messenger contact":method==="instagram"?"Instagram username or profile link":"Contact detail");
}
function updateBookingStatus(message,state=""){
  if(!status)return;
  form?.classList.toggle("is-success",state==="success");
  form?.classList.toggle("is-warning",state==="error");
  form?.classList.toggle("is-submitting",state==="busy");
  if(window.TokiMotion?.updateText)window.TokiMotion.updateText(status,message);
  else status.textContent=message;
}
updateDateLimits();
updateContactInput();
preferredDate?.addEventListener("change",updateDateLimits);
preferredDate?.addEventListener("input",updateDateLimits);
preferredTime?.addEventListener("input",updateDateLimits);
alternateDate?.addEventListener("change",updateDateLimits);
contactMethod?.addEventListener("change",updateContactInput);

form?.addEventListener("submit",async event=>{
  event.preventDefault();
  if(!form||!bookingButton||form.dataset.submitting==="true")return;
  updateDateLimits();
  if(!form.reportValidity())return;
  const turnstileToken=readTurnstileToken();
  if(!turnstileToken){
    updateBookingStatus("Please complete the human-verification challenge before sending your request.","error");
    turnstileContainer?.scrollIntoView({behavior:reducedMotion?"auto":"smooth",block:"center"});
    return;
  }
  const data=new FormData(form);
  const participants=Number(data.get("participants"));
  const payload={
    kind:"toki_booking",
    turnstileToken,
    website:(data.get("website")||"").toString(),
    name:(data.get("name")||"").toString().trim(),
    contact_method:(data.get("contact_method")||"").toString(),
    contact_value:(data.get("contact_value")||"").toString().trim(),
    session_type:(data.get("session")||"").toString(),
    preferred_date:(data.get("preferred_date")||"").toString(),
    alternate_date:(data.get("alternate_date")||"").toString()||null,
    preferred_time:(data.get("preferred_time")||"").toString(),
    location:(data.get("location")||"").toString().trim(),
    participants,
    notes:(data.get("notes")||"").toString().trim(),
    privacy_consent:form.querySelector('input[name="privacy_consent"]')?.checked===true,
    booking_terms_consent:form.querySelector('input[name="booking_terms_consent"]')?.checked===true,
    booking_terms_version:form.dataset.bookingTermsVersion||""
  };
  form.dataset.submitting="true";
  bookingButton.disabled=true;
  bookingButton.innerHTML="SENDING REQUEST…";
  updateBookingStatus("Sending your request securely. Please keep this page open for confirmation.","busy");
  try{
    const response=await fetch(TOKI_BOOKING_ENDPOINT,{
      method:"POST",
      headers:{
        "apikey":TOKI_SUPABASE_PUBLISHABLE_KEY,
        "Content-Type":"application/json"
      },
      body:JSON.stringify(payload),
      cache:"no-store"
    });
    let result={};
    try{result=await response.json();}catch(error){result={};}
    if(!response.ok||result.ok!==true||typeof result.reference_code!=="string"){
      const message=typeof result.message==="string"?result.message:
        response.status===429?"Too many requests. Please wait a little before trying again.":"We could not confirm that your request was saved. Please try again or message us through our official social page.";
      throw new Error(message);
    }
    const reference=result.reference_code;
    form.reset();
    form.classList.remove("is-prefilled");
    sessionCards.forEach(card=>{
      card.classList.remove("is-selected");
      card.querySelector(".package-link")?.setAttribute("aria-pressed","false");
    });
    updateDateLimits();
    updateContactInput();
    updateSessionDurationNote();
    updateBookingStatus("Request received. Your reference is "+reference+". We’ll review the details and contact you through your selected channel. Your date is not reserved until we send written confirmation. No payment has been taken; for paid sessions, payment instructions follow only after the final details and price are agreed.","success");
  }catch(error){
    const message=error instanceof Error?error.message:"The booking service could not be reached. Please try again or contact us through Facebook or Instagram.";
    updateBookingStatus(message+" Your entries are still here; you can retry or message our official page.","error");
  }finally{
    resetTurnstile();
    form.dataset.submitting="false";
    bookingButton.disabled=false;
    bookingButton.innerHTML=submitLabel;
    form.classList.remove("is-submitting");
  }
});
const year=document.querySelector("#year");if(year)year.textContent=String(new Date().getFullYear());
})();

// Adaptive orientation: expose the current orientation to CSS/tests and reset the open menu when the layout changes.
(function(){
  const portrait=window.matchMedia("(orientation: portrait)");
  const apply=()=>{document.documentElement.dataset.orientation=portrait.matches?"portrait":"landscape";};
  apply();
  const onChange=()=>{
    apply();
    const openNav=document.querySelector(".primary-nav.is-open");
    if(openNav)document.querySelector(".menu-toggle")?.click();
  };
  portrait.addEventListener?.("change",onChange);
})();
