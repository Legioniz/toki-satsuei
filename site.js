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
  if(!menuButton||!nav)return Promise.resolve();
  let transition=Promise.resolve();
  if(window.TokiMotion?.setMenuOpen)transition=window.TokiMotion.setMenuOpen(menuButton,nav,open);
  else{
    nav.classList.toggle("is-open",open);
    menuButton.setAttribute("aria-expanded",String(open));
    menuButton.setAttribute("aria-label",open?"Close navigation":"Open navigation");
  }
  if(open)window.TokiMotion?.setHeaderVisible(true);
  if(!open&&returnFocus)transition.then(()=>menuButton.focus({preventScroll:true}));
  return transition;
}
if(menuButton&&nav){
  menuButton.addEventListener("click",()=>setMenuOpen(menuButton.getAttribute("aria-expanded")!=="true"));
  nav.querySelectorAll("a").forEach(link=>link.addEventListener("click",()=>setMenuOpen(false,true)));
  document.addEventListener("click",event=>{
    if(nav.classList.contains("is-open")&&!siteHeader?.contains(event.target))setMenuOpen(false);
  });
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"&&nav.classList.contains("is-open")){event.preventDefault();setMenuOpen(false,true);}
  });
  window.matchMedia("(min-width: 821px)").addEventListener?.("change",event=>{if(event.matches)setMenuOpen(false);});
}

// Native Web Audio Synthesizer (0 external network requests, 100% original darkroom sound design)
const TokiSFX = (() => {
  let ctx = null;
  let enabled = true;

  function getAudioContext() {
    if (!ctx && (window.AudioContext || window.webkitAudioContext)) {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (ctx && ctx.state === "suspended") {
      ctx.resume().catch(() => {});
    }
    return ctx;
  }

  function playTone(freq, duration, type="sine", gainVal=0.04) {
    if (!enabled) return;
    try {
      const audioCtx = getAudioContext();
      if (!audioCtx) return;
      if (audioCtx.state === "suspended") audioCtx.resume();
      const t = audioCtx.currentTime;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, t);
      gain.gain.setValueAtTime(gainVal, t);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + duration);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start(t);
      osc.stop(t + duration);
    } catch {}
  }

  function playShutter() {
    if (!enabled) return;
    try {
      const audioCtx = getAudioContext();
      if (!audioCtx) return;
      if (audioCtx.state === "suspended") audioCtx.resume();
      const t = audioCtx.currentTime;
      const dur = 0.045;
      const buffer = audioCtx.createBuffer(1, Math.floor(audioCtx.sampleRate * dur), audioCtx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < data.length; i++) {
        data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (data.length * 0.25));
      }
      const noise = audioCtx.createBufferSource();
      noise.buffer = buffer;
      const filter = audioCtx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.setValueAtTime(2000, t);
      filter.Q.setValueAtTime(2, t);
      const gain = audioCtx.createGain();
      gain.gain.setValueAtTime(0.07, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + dur);
      noise.connect(filter);
      filter.connect(gain);
      gain.connect(audioCtx.destination);
      noise.start(t);
      setTimeout(() => playTone(980, 0.02, "sine", 0.025), 20);
    } catch {}
  }

  function playFocus() {
    playTone(1350, 0.025, "sine", 0.025);
  }

  function playSelect() {
    playTone(840, 0.03, "triangle", 0.035);
  }

  function setEnabled() {
    enabled = true;
  }

  function init() {
    enabled = true;
    document.querySelectorAll(".sound-toggle").forEach(btn => btn.remove());
    const unlock = () => {
      getAudioContext();
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
      window.removeEventListener("touchstart", unlock);
    };
    window.addEventListener("pointerdown", unlock, { passive: true });
    window.addEventListener("keydown", unlock, { passive: true });
    window.addEventListener("touchstart", unlock, { passive: true });
  }

  return { init, playShutter, playFocus, playSelect, setEnabled, isEnabled: () => true };
})();

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", TokiSFX.init, { once: true });
} else {
  TokiSFX.init();
}

let scrollTicking=false;

function updatePageChrome(){
  const root=document.documentElement,currentY=window.scrollY;
  const progress=Math.min(1,Math.max(0,currentY/Math.max(1,root.scrollHeight-window.innerHeight)));
  if(progressBar)progressBar.style.transform="scaleX("+progress+")";
  siteHeader?.classList.toggle("is-scrolled",currentY>28);
  backToTop?.classList.toggle("is-visible",currentY>520);
  scrollTicking=false;
}

window.addEventListener("scroll",()=>{
  if(!scrollTicking){
    requestAnimationFrame(updatePageChrome);
    scrollTicking=true;
  }
},{passive:true});
let lastViewportOrientation=window.matchMedia("(orientation: portrait)").matches?"portrait":"landscape";
function syncViewportOrientation(){
  const nextOrientation=window.matchMedia("(orientation: portrait)").matches?"portrait":"landscape";
  if(nextOrientation!==lastViewportOrientation){
    lastViewportOrientation=nextOrientation;
    if(nav?.classList.contains("is-open"))setMenuOpen(false);
  }
  updatePageChrome();
}
window.addEventListener("resize",syncViewportOrientation,{passive:true});
window.addEventListener("orientationchange",()=>{
  requestAnimationFrame(syncViewportOrientation);
},{passive:true});
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

if (!window.TokiMotion) {
  document.documentElement.classList.add("motion-ready");
  document.querySelectorAll("[data-reveal]").forEach(target => target.classList.add("is-visible"));
}
reduceMotionQuery.addEventListener?.("change", event => {
  reducedMotion = event.matches;
  if (reducedMotion) {
    heroPhoto?.style.removeProperty("--hero-pan-x");
    heroPhoto?.style.removeProperty("--hero-pan-y");
  }
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

// Smooth in-page navigation with header-aware cinematic scroll & darkroom audio
document.querySelectorAll('a[href^="#"]').forEach(link=>{
  link.addEventListener("click",event=>{
    const hash=link.getAttribute("href");
    if(!hash||hash==="#")return;
    if(hash==="#top"){
      event.preventDefault();
      window.scrollTo({top:0,behavior:reducedMotion?"auto":"smooth"});
      TokiSFX.playFocus();
      return;
    }
    const target=document.querySelector(hash);
    if(target){
      event.preventDefault();
      target.scrollIntoView({behavior:reducedMotion?"auto":"smooth",block:"start"});
      TokiSFX.playSelect();
      if(history.pushState)history.pushState(null,"",hash);
    }
  });
});

// Tactile audio feedback on primary controls and darkroom cards
document.querySelectorAll(".button, .filter-button, .calendar-controls button, .calc-apply-btn, .package-link, .menu-toggle, .lightbox-nav, .lightbox-close").forEach(btn=>{
  btn.addEventListener("click",()=>TokiSFX.playSelect(),{passive:true});
});
document.querySelectorAll(".gallery-card").forEach(card=>{
  card.addEventListener("click",()=>TokiSFX.playShutter(),{passive:true});
});

let galleryFilterRevision=0;
const galleryCards=[...document.querySelectorAll(".gallery-card")];
const filterButtons=[...document.querySelectorAll(".filter-button")];
filterButtons.forEach((button,idx)=>button.addEventListener("keydown",event=>{
  if(event.key!=="ArrowRight"&&event.key!=="ArrowLeft")return;
  event.preventDefault();
  const nextIdx=(idx+(event.key==="ArrowRight"?1:-1)+filterButtons.length)%filterButtons.length;
  filterButtons[nextIdx].focus();
  filterButtons[nextIdx].click();
}));
document.querySelectorAll(".filter-button").forEach(button=>button.addEventListener("click",()=>{
  const filter=button.dataset.filter,revision=++galleryFilterRevision;
  document.querySelectorAll(".filter-button").forEach(item=>{
    const active=item===button;item.classList.toggle("is-active",active);item.setAttribute("aria-pressed",String(active));
  });
  let staggerIndex=0;
  galleryCards.forEach(card=>{
    card.getAnimations?.().forEach(animation=>animation.cancel());
    const visible=filter==="all"||card.dataset.category===filter;
    if(visible){
      const delay=(staggerIndex++)*55;
      card.hidden=false;
      if(!reducedMotion&&card.animate)card.animate([
        {opacity:0,transform:"translateY(26px) scale(0.92) rotate(-1.5deg)",filter:"blur(4px) brightness(1.3)"},
        {opacity:1,transform:"translateY(0) scale(1) rotate(0deg)",filter:"blur(0) brightness(1)"}
      ],{duration:440,delay,easing:"cubic-bezier(0.16, 1, 0.3, 1)",fill:"backwards"});
    }else if(!reducedMotion&&card.animate){
      const fade=card.animate([
        {opacity:1,transform:"translateY(0) scale(1)"},
        {opacity:0,transform:"translateY(16px) scale(0.92)"}
      ],{duration:170,easing:"ease-in"});
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
let lightboxCards=[],lightboxIndex=0,touchStartX=0,touchStartY=0,lightboxReturnFocus=null,lightboxFrameRevision=0;
function renderLightboxFrame(direction=0){
  const card=lightboxCards[lightboxIndex];if(!card)return;
  const revision=++lightboxFrameRevision;
  lightboxImage?.getAnimations?.().forEach(animation=>animation.cancel());
  const updateImage=()=>{
    if(revision!==lightboxFrameRevision)return;
    lightboxImage.src=card.dataset.full;
    lightboxImage.alt=card.querySelector("img")?.alt||card.dataset.title||"TOKI SATSUEI photograph";
  };
  if(lightboxImage.getAttribute("src")&&!reducedMotion&&lightboxImage.animate){
    const offset=direction===0?0:direction*44;
    const exit=lightboxImage.animate([
      {opacity:1,transform:"translateX(0) scale(1)",filter:"brightness(1)"},
      {opacity:0,transform:`translateX(${-offset}px) scale(0.96)`,filter:"brightness(1.4) blur(3px)"}
    ],{duration:140,easing:"ease-in",fill:"both"});
    exit.finished.then(()=>{
      if(revision!==lightboxFrameRevision)return;
      updateImage();
      if(revision!==lightboxFrameRevision)return;
      lightboxImage.animate([
        {opacity:0,transform:`translateX(${offset}px) scale(0.96)`,filter:"brightness(1.4) blur(3px)"},
        {opacity:1,transform:"translateX(0) scale(1)",filter:"brightness(1) blur(0)"}
      ],{duration:320,easing:"cubic-bezier(0.16, 1, 0.3, 1)",fill:"both"});
    }).catch(()=>{if(revision===lightboxFrameRevision)updateImage();});
  }else if(lightboxImage.getAttribute("src")&&window.TokiMotion?.swap){
    window.TokiMotion.swap(lightboxImage,updateImage,{duration:110,enterDuration:230});
  }else updateImage();
  lightboxTitle.textContent=card.dataset.title||"";
  lightboxCaption.textContent=card.dataset.caption||"";
  lightboxPosition.textContent=String(lightboxIndex+1).padStart(2,"0")+" / "+String(lightboxCards.length).padStart(2,"0");
  const multiple=lightboxCards.length>1;
  lightboxPrevious.disabled=!multiple;lightboxNext.disabled=!multiple;
}
function openLightbox(card,triggerEvent){
  lightboxReturnFocus=document.activeElement;
  lightboxCards=visibleGalleryCards();
  lightboxIndex=Math.max(0,lightboxCards.indexOf(card));
  window.TokiMotion?.triggerShutterFlash?.(triggerEvent?.clientX,triggerEvent?.clientY,"gold");
  renderLightboxFrame(0);
  if(!lightbox.open)lightbox.showModal();
}
function stepLightbox(direction){
  if(!lightbox.open||lightboxCards.length<2)return;
  lightboxIndex=(lightboxIndex+direction+lightboxCards.length)%lightboxCards.length;
  TokiSFX.playShutter();
  renderLightboxFrame(direction);
}
galleryCards.forEach(card=>card.addEventListener("click",event=>openLightbox(card,event)));
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
lightbox?.addEventListener("close",()=>{lightboxFrameRevision+=1;lightboxImage?.getAnimations?.().forEach(animation=>animation.cancel());lightboxImage?.removeAttribute("src");lightboxCards=[];lightboxIndex=0;const returnTarget=lightboxReturnFocus;lightboxReturnFocus=null;if(returnTarget&&typeof returnTarget.focus==="function")window.setTimeout(()=>returnTarget.focus({preventScroll:true}),0);});
document.addEventListener("keydown",event=>{
  if(!lightbox?.open)return;
  if(event.key==="ArrowRight"){event.preventDefault();stepLightbox(1);}
  else if(event.key==="ArrowLeft"){event.preventDefault();stepLightbox(-1);}
});

const sessionSelect=form?.querySelector('select[name="session"]');
const sessionDurationNote=form?.querySelector("#session-duration-note");
const participantInput=form?.querySelector('input[name="participants"]');
const sessionCards=[...document.querySelectorAll(".package-card[data-session]")];
function updateParticipantConstraint(){
  if(!participantInput)return;
  const duoSelected=sessionSelect?.value==="Duo Session";
  const count=Number(participantInput.value);
  participantInput.setCustomValidity(duoSelected&&(!Number.isInteger(count)||count<2)
    ?"A Duo Session requires at least two participants.":"");
}
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
sessionSelect?.addEventListener("change",()=>{
  updateSessionDurationNote();
  updateParticipantConstraint();
  const value=sessionSelect.value;
  sessionCards.forEach(item=>{
    const active=item.dataset.session===value;
    item.classList.toggle("is-selected",active);
    item.querySelector(".package-link")?.setAttribute("aria-pressed",String(active));
  });
  const calcSelect=document.querySelector("#calc-package-select");
  if(calcSelect&&value&&calcSelect.value!==value&&[...calcSelect.options].some(opt=>opt.value===value)){
    calcSelect.value=value;
    calcSelect.dispatchEvent(new Event("change",{bubbles:true}));
  }
});
participantInput?.addEventListener("input",updateParticipantConstraint);
updateSessionDurationNote();
updateParticipantConstraint();
function selectSession(card,{moveToForm=true}={}) {
  if(!card)return;
  if(!form||!sessionSelect){
    const target=new URL("./booking.html",window.location.href);
    if(card.dataset.session)target.searchParams.set("session",card.dataset.session);
    window.location.assign(target.toString());
    return;
  }
  sessionCards.forEach(item=>{
    const selected=item===card;
    item.classList.toggle("is-selected",selected);
    item.querySelector(".package-link")?.setAttribute("aria-pressed",String(selected));
  });
  sessionSelect.value=card.dataset.session;
  sessionSelect.dispatchEvent(new Event("change",{bubbles:true}));
  const calcSelect=document.querySelector("#calc-package-select");
  if(calcSelect&&[...calcSelect.options].some(opt=>opt.value===card.dataset.session)){
    calcSelect.value=card.dataset.session;
    calcSelect.dispatchEvent(new Event("change",{bubbles:true}));
  }
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
const contactValueLabel=form?.querySelector("#contact-value-label");
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
// The Turnstile script is loaded with async/defer. Use the load event rather than
// turnstile.ready(), which Cloudflare rejects when those script attributes are present.
if(document.readyState==="complete")mountTurnstile();
else window.addEventListener("load",mountTurnstile,{once:true});
window.addEventListener("toki-turnstile-ready",mountTurnstile);
function readTurnstileToken(){
  if(!turnstileWidgetId&&window.turnstile?.render)mountTurnstile();
  if(!window.turnstile?.getResponse)return "";
  return (turnstileWidgetId?window.turnstile.getResponse(turnstileWidgetId):window.turnstile.getResponse())||"";
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
function applyBookingQueryPrefill(){
  if(!form)return;
  const params=new URLSearchParams(window.location.search);
  const allowedSessions=new Set(["Quick Snap","Toki Portraits","Signature Session","Duo Session","Outdoor session","Event coverage","Custom session"]);
  const requestedSession=params.get("session");
  if(requestedSession&&allowedSessions.has(requestedSession)&&sessionSelect){
    sessionSelect.value=requestedSession;
    sessionSelect.dispatchEvent(new Event("change",{bubbles:true}));
  }
  const participantInput=form.querySelector('input[name="participants"]');
  const requestedParticipants=Number(params.get("participants"));
  if(participantInput&&Number.isInteger(requestedParticipants)&&requestedParticipants>=1&&requestedParticipants<=12){
    participantInput.value=String(requestedSession==="Duo Session"?Math.max(2,requestedParticipants):requestedParticipants);
  }
  const photoInput=form.querySelector('input[name="additional_photos"]');
  const requestedPhotos=Number(params.get("additional_photos"));
  if(photoInput&&Number.isInteger(requestedPhotos)&&requestedPhotos>=0&&requestedPhotos<=50){
    photoInput.value=String(requestedPhotos);
  }
  const timeInput=form.querySelector('input[name="additional_time"]');
  const requestedTime=Number(params.get("additional_time"));
  if(timeInput&&Number.isInteger(requestedTime)&&requestedTime>=0&&requestedTime<=120&&requestedTime%15===0){
    timeInput.value=String(requestedTime);
  }
  const requestedDate=params.get("date")||"";
  if(/^\d{4}-\d{2}-\d{2}$/.test(requestedDate)&&requestedDate>=manilaNow().date){
    const parsedDate=new Date(requestedDate+"T00:00:00Z");
    if(Number.isFinite(parsedDate.getTime())&&parsedDate.toISOString().slice(0,10)===requestedDate&&preferredDate){
      preferredDate.value=requestedDate;
    }
  }
  const notesField=form.querySelector('textarea[name="notes"]');
  const addOns=[];
  if(Number.isInteger(requestedPhotos)&&requestedPhotos>0&&requestedPhotos<=50){
    addOns.push(requestedPhotos+" extra edited photo"+(requestedPhotos===1?"":"s"));
  }
  if(Number.isInteger(requestedTime)&&requestedTime>0&&requestedTime<=120&&requestedTime%15===0){
    addOns.push(requestedTime+" min extra time");
  }
  if(notesField&&addOns.length)notesField.value="Requested add-ons: "+addOns.join(", ")+".";
  updateDateLimits();
  updateContactInput();
  updateSessionDurationNote();
  updateParticipantConstraint();
  const dateWasApplied=Boolean(requestedDate)&&preferredDate?.value===requestedDate;
  const messages=[];
  if(requestedSession&&allowedSessions.has(requestedSession))messages.push("Selected "+requestedSession+".");
  if(dateWasApplied){
    const formattedDate=new Intl.DateTimeFormat("en-PH",{timeZone:"Asia/Manila",dateStyle:"long"}).format(new Date(requestedDate+"T00:00:00+08:00"));
    messages.push("You selected "+formattedDate+".");
    if(params.get("source")==="availability-calendar"){
      messages.push("The public calendar is a guide only. We will confirm the exact time with you in writing.");
      const confirmedWindows=Number(params.get("confirmed_windows"));
      if(Number.isInteger(confirmedWindows)&&confirmedWindows>0&&confirmedWindows<=1000){
        messages.push("The calendar showed "+confirmedWindows+" confirmed time windows when you selected this date; you may request another non-overlapping time, subject to confirmation.");
      }
    }
    messages.push("This is an inquiry only; your session is not reserved until TOKI SATSUEI confirms it in writing.");
  }
  if(messages.length&&status)status.textContent=messages.join(" ");
}
function updateContactInput(){
  if(!contactMethod||!contactValue)return;
  const method=contactMethod.value;
  contactValue.type=method==="email"?"email":"text";
  contactValue.autocomplete=method==="email"?"email":"off";
  contactValue.inputMode=method==="email"?"email":"text";
  contactValue.placeholder=method==="instagram"?"Instagram username or profile link":method==="facebook"?"Facebook profile or Messenger contact":method==="email"?"Email address":"Select channel first";
  const detailLabel=method==="email"?"Email address":method==="facebook"?"Facebook Messenger contact":method==="instagram"?"Instagram handle or profile link":"Your contact detail";
  contactValue.setAttribute("aria-label",detailLabel);
  if(contactValueLabel)contactValueLabel.textContent=detailLabel;
}
function extractBookingPayload(formElement,turnstileToken){
  const data=new FormData(formElement);
  const participants=Number(data.get("participants"));
  const payload={
    kind:"toki_booking",
    turnstileToken:String(turnstileToken||""),
    website:String(data.get("website")||""),
    name:String(data.get("name")||"").trim(),
    contact_method:String(data.get("contact_method")||""),
    contact_value:String(data.get("contact_value")||"").trim(),
    session_type:String(data.get("session")||""),
    preferred_date:String(data.get("preferred_date")||""),
    alternate_date:String(data.get("alternate_date")||"")||null,
    preferred_time:String(data.get("preferred_time")||""),
    location:String(data.get("location")||"").trim(),
    participants,
    additional_photos: Number(data.get("additional_photos")||"0"),
    additional_time: Number(data.get("additional_time")||"0"),
    notes:String(data.get("notes")||"").trim(),
    privacy_consent:formElement.querySelector('input[name="privacy_consent"]')?.checked===true,
    booking_terms_consent:formElement.querySelector('input[name="booking_terms_consent"]')?.checked===true,
    booking_terms_version:formElement.dataset.bookingTermsVersion||""
  };
  const allowedSessions=["Quick Snap","Toki Portraits","Signature Session","Duo Session","Outdoor session","Event coverage","Custom session"];
  const valid=payload.name.length>=1&&payload.name.length<=100
    &&["instagram","facebook","email"].includes(payload.contact_method)
    &&payload.contact_value.length>=2&&payload.contact_value.length<=254
    &&(payload.contact_method!=="email"||/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.contact_value))
    &&allowedSessions.includes(payload.session_type)
    &&/^\d{4}-\d{2}-\d{2}$/.test(payload.preferred_date)
    &&(!payload.alternate_date||(/^\d{4}-\d{2}-\d{2}$/.test(payload.alternate_date)&&payload.alternate_date!==payload.preferred_date))
    &&/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(payload.preferred_time)
    &&payload.location.length>=2&&payload.location.length<=200
    &&Number.isInteger(payload.participants)&&payload.participants>=1&&payload.participants<=12
    &&(payload.session_type!=="Duo Session"||payload.participants>=2)
    &&Number.isInteger(payload.additional_photos)&&payload.additional_photos>=0&&payload.additional_photos<=50
    &&Number.isInteger(payload.additional_time)&&payload.additional_time>=0&&payload.additional_time<=120&&payload.additional_time%15===0
    &&payload.notes.length>=10&&payload.notes.length<=2000
    &&payload.privacy_consent&&payload.booking_terms_consent
    &&payload.booking_terms_version==="2026-11-16-v1"
    &&payload.turnstileToken.length>0;
  if(!valid)return {valid:false,error:"Please review your booking details, contact information, date, time, and required confirmations."};
  return {valid:true,payload};
}

function updateBookingStatus(message,state=""){
  if(!status)return;
  form?.classList.toggle("is-success",state==="success");
  form?.classList.toggle("is-warning",state==="error");
  form?.classList.toggle("is-submitting",state==="busy");
  status.textContent=message;
}
updateDateLimits();
updateContactInput();
applyBookingQueryPrefill();
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
  const extracted=extractBookingPayload(form,turnstileToken);
  if(!extracted.valid){
    updateBookingStatus(extracted.error,"error");
    form.reportValidity();
    return;
  }
  const payload=extracted.payload;
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
    const refCard=form.querySelector("#booking-reference-card");
    const refCodeInput=form.querySelector("#booking-reference-code");
    form.reset();
    if(refCard&&refCodeInput){
      refCodeInput.value=reference;
      refCard.classList.remove("is-hidden");
    }
    form.classList.remove("is-prefilled");
    sessionCards.forEach(card=>{
      card.classList.remove("is-selected");
      card.querySelector(".package-link")?.setAttribute("aria-pressed","false");
    });
    updateDateLimits();
    updateContactInput();
    updateSessionDurationNote();
    updateParticipantConstraint();
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

// Before & After comparison slider
(function initComparisonSlider(){
  const slider=document.querySelector("#photo-comparison");
  if(!slider)return;
  const divider=slider.querySelector(".comparison-divider");
  const handle=slider.querySelector(".comparison-handle");
  const afterWrap=slider.querySelector(".comparison-image-after");
  if(!divider||!handle||!afterWrap)return;

  let isDragging=false;
  function setPosition(percentage){
    const clamped=Math.max(0,Math.min(100,percentage));
    slider.style.setProperty("--split-pos",clamped.toFixed(2)+"%");
    handle.setAttribute("aria-valuenow",String(Math.round(clamped)));
  }

  function onPointerMove(e){
    if(!isDragging)return;
    const rect=slider.getBoundingClientRect();
    const x=e.clientX-rect.left;
    setPosition((x/rect.width)*100);
  }

  function stopDragging(){
    if(isDragging){
      isDragging=false;
      slider.classList.remove("is-dragging");
      window.removeEventListener("pointermove",onPointerMove);
      window.removeEventListener("pointerup",stopDragging);
      window.removeEventListener("pointercancel",stopDragging);
    }
  }

  divider.addEventListener("pointerdown",()=>{
    isDragging=true;
    slider.classList.add("is-dragging");
    window.addEventListener("pointermove",onPointerMove);
    window.addEventListener("pointerup",stopDragging);
    window.addEventListener("pointercancel",stopDragging);
  });

  handle.addEventListener("keydown",e=>{
    const current=parseFloat(getComputedStyle(slider).getPropertyValue("--split-pos"))||50;
    if(e.key==="ArrowLeft"||e.key==="ArrowDown"){
      e.preventDefault();
      setPosition(current-5);
    }else if(e.key==="ArrowRight"||e.key==="ArrowUp"){
      e.preventDefault();
      setPosition(current+5);
    }else if(e.key==="Home"){
      e.preventDefault();
      setPosition(0);
    }else if(e.key==="End"){
      e.preventDefault();
      setPosition(100);
    }
  });
})();

// Interactive Pricing Calculator
(function initPricingCalculator(){
  const calc=document.querySelector("#pricing-calculator");
  if(!calc)return;

  const packageSelect=calc.querySelector("#calc-package-select");
  const partInput=calc.querySelector("#calc-part-qty");
  const btnPartMinus=calc.querySelector("#calc-part-minus");
  const btnPartPlus=calc.querySelector("#calc-part-plus");
  const photoInput=calc.querySelector("#calc-photo-qty");
  const btnPhotoMinus=calc.querySelector("#calc-photo-minus");
  const btnPhotoPlus=calc.querySelector("#calc-photo-plus");
  const timeInput=calc.querySelector("#calc-time-qty");
  const btnTimeMinus=calc.querySelector("#calc-time-minus");
  const btnTimePlus=calc.querySelector("#calc-time-plus");

  const breakdownList=calc.querySelector("#calc-breakdown-list");
  const totalDisplay=calc.querySelector("#calc-total-display");
  const btnApply=calc.querySelector("#calc-apply-to-booking");

  const RATES={
    "Quick Snap":{base:200,includedParticipants:1,duration:15},
    "Toki Portraits":{base:350,includedParticipants:1,duration:30},
    "Signature Session":{base:500,includedParticipants:1,duration:60},
    "Duo Session":{base:450,includedParticipants:2,duration:30}
  };

  function syncStepper(button,input,min,max){
    if(!button||!input)return;
    const value=Number.parseInt(input.value,10);
    const current=Number.isFinite(value)?value:min;
    const disabled=button.id.endsWith("-minus")?current<=min:current>=max;
    button.disabled=disabled;
    button.setAttribute("aria-disabled",String(disabled));
  }

  function recalculate(){
    const selectedPkg=packageSelect?packageSelect.value:"Toki Portraits";
    const pkgData=RATES[selectedPkg]||RATES["Toki Portraits"];
    const participantMin=pkgData.includedParticipants===2?2:1;
    syncStepper(btnPartMinus,partInput,participantMin,12);
    syncStepper(btnPartPlus,partInput,participantMin,12);
    syncStepper(btnPhotoMinus,photoInput,0,50);
    syncStepper(btnPhotoPlus,photoInput,0,50);
    syncStepper(btnTimeMinus,timeInput,0,120);
    syncStepper(btnTimePlus,timeInput,0,120);
    const basePrice=pkgData.base;
    const participants=parseInt(partInput?.value||"1",10);
    const extraPhotos=parseInt(photoInput?.value||"0",10);
    const extraTimeMins=parseInt(timeInput?.value||"0",10);
    const extraTimeSteps=Math.floor(extraTimeMins/15);

    const extraParticipants=Math.max(0,participants-pkgData.includedParticipants);
    const participantAddonCost=extraParticipants*50;
    const photoAddonCost=extraPhotos*30;
    const timeAddonCost=extraTimeSteps*75;
    const addonsTotal=participantAddonCost+photoAddonCost+timeAddonCost;
    const grandTotal=basePrice+addonsTotal;
    const deposit=Math.round(grandTotal*0.20);

    if(totalDisplay){
      const nextText="₱"+grandTotal.toLocaleString();
      const changed=totalDisplay.textContent!==nextText;
      totalDisplay.textContent=nextText;
      if(changed)window.TokiMotion?.pulseMetric?.(totalDisplay);
    }

    if(breakdownList){
      let items=`<li><span>Base: ${selectedPkg}</span><strong>₱${basePrice.toLocaleString()}</strong></li>`;
      if(extraParticipants>0){
        items+=`<li><span>Extra Participants (${extraParticipants} × ₱50)</span><strong>₱${participantAddonCost.toLocaleString()}</strong></li>`;
      }
      if(extraPhotos>0){
        items+=`<li><span>Additional Edited Photos (${extraPhotos} × ₱30)</span><strong>₱${photoAddonCost.toLocaleString()}</strong></li>`;
      }
      if(extraTimeSteps>0){
        items+=`<li><span>Additional Time (${extraTimeMins} mins)</span><strong>₱${timeAddonCost.toLocaleString()}</strong></li>`;
      }
      items+=`<li style="border-top:1px dashed #403831;padding-top:6px;margin-top:6px;"><span>20% Reservation Deposit (est.)</span><strong>₱${deposit.toLocaleString()}</strong></li>`;
      breakdownList.innerHTML=items;
      if(!reducedMotion&&breakdownList.querySelectorAll){
        breakdownList.querySelectorAll("li").forEach((li,idx)=>{
          li.animate?.([
            {opacity:0,transform:"translateX(-12px)"},
            {opacity:1,transform:"translateX(0)"}
          ],{duration:280,delay:idx*40,easing:"cubic-bezier(0.16, 1, 0.3, 1)",fill:"backwards"});
        });
      }
    }
  }

  packageSelect?.addEventListener("change",()=>{
    if(packageSelect.value==="Duo Session"&&parseInt(partInput?.value||"1",10)<2){
      if(partInput)partInput.value="2";
    }
    recalculate();
  });

  btnPartMinus?.addEventListener("click",()=>{
    const cur=parseInt(partInput?.value||"1",10);
    const min=(packageSelect?.value==="Duo Session")?2:1;
    if(cur>min){
      if(partInput)partInput.value=String(cur-1);
      recalculate();
    }
  });

  btnPartPlus?.addEventListener("click",()=>{
    const cur=parseInt(partInput?.value||"1",10);
    if(cur<12){
      if(partInput)partInput.value=String(cur+1);
      recalculate();
    }
  });

  btnPhotoMinus?.addEventListener("click",()=>{
    const cur=parseInt(photoInput?.value||"0",10);
    if(cur>0){
      if(photoInput)photoInput.value=String(cur-1);
      recalculate();
    }
  });

  btnPhotoPlus?.addEventListener("click",()=>{
    const cur=parseInt(photoInput?.value||"0",10);
    if(cur<50){
      if(photoInput)photoInput.value=String(cur+1);
      recalculate();
    }
  });

  btnTimeMinus?.addEventListener("click",()=>{
    const cur=parseInt(timeInput?.value||"0",10);
    if(cur>=15){
      if(timeInput)timeInput.value=String(cur-15);
      recalculate();
    }
  });

  btnTimePlus?.addEventListener("click",()=>{
    const cur=parseInt(timeInput?.value||"0",10);
    if(cur<120){
      if(timeInput)timeInput.value=String(cur+15);
      recalculate();
    }
  });

  btnApply?.addEventListener("click",()=>{
    const formElement=document.querySelector("#inquiry-form");
    const selectedPkg=packageSelect?packageSelect.value:"Toki Portraits";
    const participants=partInput?partInput.value:"1";
    const extraPhotos=parseInt(photoInput?.value||"0",10);
    const extraTimeMins=parseInt(timeInput?.value||"0",10);
    if(!formElement){
      const target=new URL("./booking.html",window.location.href);
      target.searchParams.set("session",selectedPkg);
      target.searchParams.set("participants",String(participants));
      target.searchParams.set("additional_photos",String(extraPhotos));
      target.searchParams.set("additional_time",String(extraTimeMins));
      window.location.assign(target.toString());
      return;
    }
    const sessionField=formElement.querySelector('select[name="session"]');
    const participantsField=formElement.querySelector('input[name="participants"]');
    const photosField=formElement.querySelector('input[name="additional_photos"]');
    const timeField=formElement.querySelector('input[name="additional_time"]');
    const notesField=formElement.querySelector('textarea[name="notes"]');

    if(sessionField){
      sessionField.value=selectedPkg;
      sessionField.dispatchEvent(new Event("change",{bubbles:true}));
    }
    if(participantsField){
      participantsField.value=String(participants);
      participantsField.dispatchEvent(new Event("change",{bubbles:true}));
    }
    if(photosField){
      photosField.value=String(extraPhotos);
      photosField.dispatchEvent(new Event("change",{bubbles:true}));
    }
    if(timeField){
      timeField.value=String(extraTimeMins);
      timeField.dispatchEvent(new Event("change",{bubbles:true}));
    }
    if(notesField&&(extraPhotos>0||extraTimeMins>0)){
      const noteParts=[];
      if(extraPhotos>0)noteParts.push(extraPhotos+" extra edited photo"+(extraPhotos>1?"s":""));
      if(extraTimeMins>0)noteParts.push(extraTimeMins+" min extra time");
      const addOnText="Requested add-ons: "+noteParts.join(", ")+".";
      if(!notesField.value.includes("Requested add-ons:")){
        notesField.value=notesField.value?(notesField.value+"\n"+addOnText):addOnText;
      }
    }
    formElement.classList.remove("is-prefilled");
    void formElement.offsetWidth;
    formElement.classList.add("is-prefilled");
    window.setTimeout(()=>formElement.classList.remove("is-prefilled"),1300);
    formElement.scrollIntoView({behavior:reducedMotion?"auto":"smooth",block:"start"});
    sessionField?.focus({preventScroll:true});
  });

  recalculate();
})();

// Copy the generated request reference after a successful submission.
(function initBookingReferenceCopy(){
  const formElement=document.querySelector("#inquiry-form");
  const button=formElement?.querySelector("#btn-copy-reference");
  const codeInput=formElement?.querySelector("#booking-reference-code");
  button?.addEventListener("click",async()=>{
    if(!codeInput)return;
    try{
      if(navigator?.clipboard?.["writeText"]){
        await navigator.clipboard["writeText"](codeInput.value);
      } else {
        codeInput.select();
        document.execCommand("copy");
      }
    }catch(error){
      codeInput.select();
      try{document.execCommand("copy");}catch(copyError){}
    }
    button.textContent="Copied!";
    window.setTimeout(()=>{button.textContent="Copy Code";},2000);
  });
})();

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
    if(openNav){
      openNav.classList.remove("is-open");
      openNav.getAnimations?.().forEach(a=>a.cancel());
      const toggle=document.querySelector(".menu-toggle");
      if(toggle){
        toggle.setAttribute("aria-expanded","false");
        toggle.setAttribute("aria-label","Open navigation");
      }
    }
  };
  portrait.addEventListener?.("change",onChange);
})();
