const pageProgressBar=document.querySelector("#page-progress-bar"),archiveHeader=document.querySelector(".site-header");
const hoverHeaderEnabled=window.matchMedia("(hover: hover) and (pointer: fine)").matches;
let scrollTicking=false;
let lastScrollY=window.scrollY;
let lastScrollDirection="up";
let hoverRevealed=false;
function setArchiveHeaderHidden(hidden){
 if(!archiveHeader)return;
 const menuOpen=Boolean(archiveHeader.querySelector(".primary-nav.is-open"));
 const shouldHide=Boolean(hidden)&&window.scrollY>64&&!menuOpen;
 archiveHeader.classList.toggle("is-auto-hidden",shouldHide);
}
function updateArchiveChrome(){
 const root=document.documentElement,currentY=window.scrollY,delta=currentY-lastScrollY;
 if(currentY<=36){
  lastScrollDirection="up";hoverRevealed=false;setArchiveHeaderHidden(false);
 }else if(delta>1){
  lastScrollDirection="down";hoverRevealed=false;setArchiveHeaderHidden(true);
 }else if(delta< -1){
  lastScrollDirection="up";hoverRevealed=false;setArchiveHeaderHidden(false);
 }
 if(archiveHeader?.querySelector(".primary-nav.is-open"))setArchiveHeaderHidden(false);
 lastScrollY=currentY;
 const progress=Math.min(1,Math.max(0,currentY/Math.max(1,root.scrollHeight-window.innerHeight)));
 if(pageProgressBar)pageProgressBar.style.transform="scaleX("+progress+")";
 archiveHeader?.classList.toggle("is-scrolled",currentY>28);scrollTicking=false;
}
window.addEventListener("scroll",()=>{if(!scrollTicking){requestAnimationFrame(updateArchiveChrome);scrollTicking=true;}},{passive:true});
window.addEventListener("resize",updateArchiveChrome,{passive:true});
if(archiveHeader){
 window.addEventListener("pointermove",event=>{
  if(!hoverHeaderEnabled||event.pointerType==="touch")return;
  if(event.clientY<=40){
   hoverRevealed=true;setArchiveHeaderHidden(false);return;
  }
  if(hoverRevealed&&event.clientY>archiveHeader.offsetHeight+14){
   hoverRevealed=false;
   if(lastScrollDirection==="down"&&window.scrollY>64)setArchiveHeaderHidden(true);
  }
 },{passive:true});
 archiveHeader.addEventListener("focusin",()=>{hoverRevealed=false;setArchiveHeaderHidden(false);});
}
updateArchiveChrome();
const menuButton=document.querySelector(".menu-toggle");
const nav=document.querySelector(".primary-nav");
const archiveNavHeader=document.querySelector(".site-header");
function setArchiveMenuOpen(open,returnFocus=false){
 if(!menuButton||!nav)return;
 if(window.TokiMotion?.setMenuOpen)window.TokiMotion.setMenuOpen(menuButton,nav,open);
 else{
  nav.classList.toggle("is-open",open);
  menuButton.setAttribute("aria-expanded",String(open));
  menuButton.setAttribute("aria-label",open?"Close navigation":"Open navigation");
 }
 if(open)setArchiveHeaderHidden(false);
 if(!open&&returnFocus)menuButton.focus();
}
if(menuButton&&nav){
 menuButton.addEventListener("click",()=>setArchiveMenuOpen(menuButton.getAttribute("aria-expanded")!=="true"));
 nav.querySelectorAll("a").forEach(link=>link.addEventListener("click",()=>setArchiveMenuOpen(false)));
 document.addEventListener("click",event=>{
  if(nav.classList.contains("is-open")&&!archiveNavHeader?.contains(event.target))setArchiveMenuOpen(false);
 });
 document.addEventListener("keydown",event=>{
  if(event.key==="Escape"&&nav.classList.contains("is-open")){event.preventDefault();setArchiveMenuOpen(false,true);}
 });
 window.matchMedia("(min-width: 821px)").addEventListener?.("change",event=>{if(event.matches)setArchiveMenuOpen(false);});
}

const filters=document.querySelector("#library-filters");
const groups=document.querySelector("#library-groups");
const countLabel=document.querySelector("#library-count");
const searchInput=document.querySelector("#archive-search");
const dialog=document.querySelector("#album-dialog");
const dialogTitle=document.querySelector("#album-dialog-title");
const dialogCategory=document.querySelector("#album-dialog-category");
const dialogDescription=document.querySelector("#album-dialog-description");
const dialogCount=document.querySelector("#album-dialog-count");
const dialogPosition=document.querySelector("#album-dialog-position");
const albumProgressBar=document.querySelector("#album-progress-bar");
const mediaRail=document.querySelector("#album-media-rail");
const closeDialog=document.querySelector(".album-dialog-close");
let archiveCategories=[];
let activeCategory="all";
let activeQuery="";
let activeAlbum=null;
let albumReturnFocus=null;
let revealObserver=null;
let reducedMotion=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const motionPreference=window.matchMedia("(prefers-reduced-motion: reduce)");
motionPreference.addEventListener?.("change",event=>{reducedMotion=event.matches;if(reducedMotion)document.querySelectorAll(".reveal-on-scroll").forEach(item=>item.classList.add("is-revealed"));});
const hasViewTransitions=typeof document.startViewTransition==="function";

function element(tag,className,text){
  const node=document.createElement(tag);
  if(className)node.className=className;
  if(text!==undefined)node.textContent=text;
  return node;
}
function countWords(count,singular,plural){return count+" "+(count===1?singular:plural);}
function scrollTrack(track,direction){
  if(!track)return;
  track.scrollBy({left:Math.max(220,Math.round(track.clientWidth*.78))*direction,behavior:reducedMotion?"auto":"smooth"});
}
function normalize(value){return String(value||"").toLocaleLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").trim();}
function safePlay(video){
  const promise=video.play();
  if(promise&&typeof promise.catch==="function")promise.catch(()=>{});
}
const activeTransitions=new WeakMap();
function animateChange(node,render){
  if(!node){render();return;}
  if(reducedMotion||!node.animate){render();return;}
  const token=(activeTransitions.get(node)?.token||0)+1;
  activeTransitions.set(node,{token,animation:null});
  const fade=node.animate([{opacity:1,transform:"translateY(0)"},{opacity:0,transform:"translateY(7px)"}],{duration:110,easing:"ease-in"});
  activeTransitions.set(node,{token,animation:fade});
  fade.finished.then(()=>{
    if(activeTransitions.get(node)?.token!==token)return;
    render();
    const entrance=node.animate([{opacity:0,transform:"translateY(-5px)"},{opacity:1,transform:"translateY(0)"}],{duration:230,easing:"cubic-bezier(.2,.7,.2,1)"});
    activeTransitions.set(node,{token,animation:entrance});
  }).catch(()=>{});
}
function revealWithin(root){
  const items=root.querySelectorAll(".reveal-on-scroll");
  if(!items.length)return;
  if(reducedMotion||!("IntersectionObserver" in window)){
    items.forEach(item=>item.classList.add("is-revealed"));
    return;
  }
  if(!revealObserver){
    revealObserver=new IntersectionObserver(entries=>{
      entries.forEach(entry=>{
        if(entry.isIntersecting){
          entry.target.classList.add("is-revealed");
          revealObserver.unobserve(entry.target);
        }
      });
    },{threshold:.08,rootMargin:"0px 0px -36px 0px"});
  }
  items.forEach(item=>revealObserver.observe(item));
}
function setCount(visibleCategories){
  const albums=visibleCategories.reduce((sum,category)=>sum+category.albums.length,0);
  const frames=visibleCategories.reduce((sum,category)=>sum+category.albums.reduce((total,album)=>total+album.media.length,0),0);
  countLabel.textContent=countWords(albums,"ALBUM","ALBUMS")+"  /  "+countWords(frames,"FRAME","FRAMES");
}
function updateFilters(){
  filters.querySelectorAll("button").forEach(button=>{
    button.setAttribute("aria-pressed",String(button.dataset.category===activeCategory));
  });
}
function buildFilters(){
  filters.replaceChildren();
  const definitions=[{id:"all",title:"All collections"}].concat(archiveCategories.map(category=>({id:category.id,title:category.title})));
  definitions.forEach(item=>{
    const button=element("button","library-filter",item.title);
    button.type="button";
    button.dataset.category=item.id;
    button.setAttribute("aria-pressed",String(item.id===activeCategory));
    button.addEventListener("click",()=>{
      if(activeCategory===item.id)return;
      activeCategory=item.id;
      updateFilters();
      animateChange(groups,renderGroups);
    });
    filters.append(button);
  });
}
function arrowButton(label,direction){
  const button=element("button","rail-button",direction<0?"←":"→");
  button.type="button";
  button.setAttribute("aria-label",label);
  return button;
}
function addImageFallback(image,container){
  image.addEventListener("error",()=>{
    image.remove();
    container.classList.add("media-unavailable");
    if(!container.querySelector(".media-fallback"))container.append(element("span","media-fallback","FRAME UNAVAILABLE"));
  },{once:true});
  image.addEventListener("load",()=>image.classList.add("is-loaded"),{once:true});
}
function makeAlbumCard(category,album){
  const isCinematic=["cosplay","events"].includes(category.id);
  const cinematicLabel=category.id==="events"?"LIVE MOMENTS / EVENT ARCHIVE":"CHARACTER STUDY / COSPLAY";
  const button=element("button","album-card"+(isCinematic?" album-card--cinematic album-card--"+category.id:""));
  button.type="button";
  button.setAttribute("aria-label","Open album "+album.title+" in "+category.title);
  const cover=element("span","album-cover");
  const visual=album.media.find(item=>item.type==="image")||album.media[0];
  if(visual&&visual.type==="image"){
    const image=element("img");
    image.draggable=false;
    image.src=visual.src;image.alt="";image.loading="lazy";image.decoding="async";
    addImageFallback(image,cover);
    cover.append(image);
  }else if(visual&&visual.type==="video"){
    const video=element("video");
    video.src=visual.src;video.muted=true;video.playsInline=true;video.preload="metadata";video.loop=true;
    video.setAttribute("aria-hidden","true");
    cover.append(video,element("span","album-cover-type","VIDEO"));
    button.addEventListener("pointerenter",()=>{if(!reducedMotion)safePlay(video);});
    button.addEventListener("pointerleave",()=>{video.pause();video.currentTime=0;});
    button.addEventListener("focus",()=>{if(!reducedMotion)safePlay(video);});
    button.addEventListener("blur",()=>{video.pause();video.currentTime=0;});
  }else{
    cover.append(element("span","album-cover-mark","時"));
  }
  if(isCinematic){
    const overlay=element("span","album-cover-overlay");
    overlay.append(
      element("small","album-cover-kicker",cinematicLabel),
      element("span","album-cover-detail",countWords(album.media.length,"FRAME","FRAMES")+"  ·  OPEN ALBUM ↗")
    );
    cover.append(overlay);
  }
  const meta=element("span","album-card-meta");
  const text=element("span");
  text.append(element("strong","album-card-title",album.title));
  text.append(element("small","album-card-count",countWords(album.media.length,"frame","frames")));
  meta.append(text,element("span","album-card-arrow","↗"));
  button.append(cover,meta);
  button.addEventListener("click",()=>openAlbum(category,album));
  return button;
}
function updateRailState(rail,left,right,progress){
  const maximum=Math.max(0,rail.scrollWidth-rail.clientWidth);
  left.disabled=rail.scrollLeft<=3;
  right.disabled=rail.scrollLeft>=maximum-3;
  progress.style.transform="scaleX("+Math.max(.025,maximum?rail.scrollLeft/maximum:1)+")";
}
function enableMouseDrag(rail){
  rail.addEventListener("dragstart",event=>event.preventDefault());
  let pointerId=null;
  let originX=0;
  let originScroll=0;
  let moved=false;
  let suppressClick=false;
  rail.addEventListener("pointerdown",event=>{
    if(event.pointerType!=="mouse"||event.button!==0||event.target.closest("video,a"))return;
    pointerId=event.pointerId;
    originX=event.clientX;
    originScroll=rail.scrollLeft;
    moved=false;
    rail.classList.add("is-pointer-down");
  });
  rail.addEventListener("pointermove",event=>{
    if(pointerId!==event.pointerId)return;
    const distance=event.clientX-originX;
    if(Math.abs(distance)>5&&!moved){
      moved=true;
      rail.classList.add("is-dragging");
      rail.setPointerCapture?.(pointerId);
    }
    if(moved)rail.scrollLeft=originScroll-distance;
  });
  const finish=event=>{
    if(pointerId===null||event.pointerId!==pointerId)return;
    if(moved){suppressClick=true;window.setTimeout(()=>{suppressClick=false;},0);}
    pointerId=null;
    rail.classList.remove("is-pointer-down","is-dragging");
    if(rail.hasPointerCapture?.(event.pointerId))rail.releasePointerCapture(event.pointerId);
  };
  rail.addEventListener("pointerup",finish);
  rail.addEventListener("pointercancel",finish);
  rail.addEventListener("lostpointercapture",()=>{pointerId=null;rail.classList.remove("is-pointer-down","is-dragging");});
  rail.addEventListener("click",event=>{
    if(suppressClick){
      event.preventDefault();
      event.stopPropagation();
      suppressClick=false;
    }
  },true);
  rail.addEventListener("keydown",event=>{
    if(event.key==="ArrowRight"||event.key==="ArrowLeft"){
      event.preventDefault();
      scrollTrack(rail,event.key==="ArrowRight"?1:-1);
    }else if(event.key==="Home"||event.key==="End"){
      event.preventDefault();
      rail.scrollTo({left:event.key==="Home"?0:rail.scrollWidth,behavior:reducedMotion?"auto":"smooth"});
    }
  });
}
function makeCategoryGroup(category){
  const isCinematic=["cosplay","events"].includes(category.id);
  const section=element("section","archive-group"+(isCinematic?" archive-group--cinematic archive-group--"+category.id:"")+" reveal-on-scroll");
  const head=element("div","archive-group-head");
  const copy=element("div","archive-group-copy");
  copy.append(
    element("span","archive-group-kicker",isCinematic?(category.id==="events"?"CINEMATIC COLLECTION / FIELD STORIES":"CINEMATIC COLLECTION / CHARACTER WORLDS"):(category.code||"COLLECTION")),
    element("h2","archive-group-title",category.title),
    element("p","archive-group-description",category.description||"A collection of moments worth keeping.")
  );
  head.append(copy,element("span","archive-group-meta",countWords(category.albums.length,"ALBUM","ALBUMS")+"  ·  "+category.image_count+" FRAMES"));
  const rail=element("div","album-rail");
  rail.tabIndex=0;rail.setAttribute("role","region");rail.setAttribute("aria-label",category.title+" albums. Use arrow keys or drag to browse.");
  category.albums.forEach(album=>rail.append(makeAlbumCard(category,album)));
  const controls=element("div","archive-rail-controls");
  const left=arrowButton("Scroll "+category.title+" albums left",-1);
  const right=arrowButton("Scroll "+category.title+" albums right",1);
  const progress=element("span","archive-rail-progress");
  const progressFill=element("span","archive-rail-progress-fill");
  progress.append(progressFill);
  left.addEventListener("click",()=>scrollTrack(rail,-1));
  right.addEventListener("click",()=>scrollTrack(rail,1));
  rail.addEventListener("scroll",()=>updateRailState(rail,left,right,progressFill),{passive:true});
  controls.append(left,right);
  const railTop=element("div","archive-rail-top");
  railTop.append(progress,controls);
  enableMouseDrag(rail);
  const wrap=element("div","album-rail-wrap");
  wrap.append(railTop,rail);
  section.append(head,wrap);
  requestAnimationFrame(()=>updateRailState(rail,left,right,progressFill));
  return section;
}
function showEmpty(message,query=""){
  const empty=element("section","archive-empty");
  const currentCategory=archiveCategories.find(category=>category.id===activeCategory);
  const intro=element("div","archive-empty-intro");
  const mark=element("div","archive-empty-mark","時の記憶");
  const copy=element("div","archive-empty-copy");
  const kicker=element("p","archive-empty-kicker",query?"SEARCH THE ARCHIVE":currentCategory?"COLLECTION / "+currentCategory.code:"THE COLLECTION INDEX");
  const heading=element("h2","",message);
  const description=element("p","",query
    ?"Try another title or clear the search to browse every collection."
    :currentCategory
      ?currentCategory.description+" This shelf is ready for its first album."
      :"Six collections are ready for future shoots. Albums and photographs will appear here automatically when they are uploaded.");
  copy.append(kicker,heading,description);
  intro.append(mark,copy);
  empty.append(intro);

  if(query){
    const clear=element("button","archive-empty-action","CLEAR SEARCH");
    clear.type="button";
    clear.addEventListener("click",()=>{
      searchInput.value="";
      activeQuery="";
      renderGroups();
      searchInput.focus();
    });
    empty.append(clear);
  }else if(activeCategory==="all"&&archiveCategories.length){
    const shelfGrid=element("div","archive-shelf-grid");
    archiveCategories.forEach((category,index)=>{
      const shelf=element("button","archive-shelf");
      shelf.type="button";
      shelf.dataset.category=category.id;
      shelf.style.setProperty("--shelf-index",String(index));
      shelf.setAttribute("aria-label","Browse the "+category.title+" collection");
      const code=element("span","archive-shelf-code",category.code+" / COLLECTION");
      const title=element("strong","archive-shelf-title",category.title);
      const detail=element("span","archive-shelf-description",category.description);
      const meta=element("span","archive-shelf-meta",countWords(category.album_count,"ALBUM","ALBUMS")+"  ·  "+countWords(category.image_count,"FRAME","FRAMES"));
      const action=element("span","archive-shelf-action","OPEN COLLECTION  ↗");
      shelf.append(code,title,detail,meta,action);
      shelf.addEventListener("click",()=>{
        activeCategory=category.id;
        updateFilters();
        animateChange(groups,renderGroups);
        const activeFilter=filters.querySelector('[data-category="'+category.id+'"]');
        activeFilter?.focus({preventScroll:true});
      });
      shelfGrid.append(shelf);
    });
    empty.append(shelfGrid);
    const guide=element("a","archive-upload-guide","HOW TO ADD PHOTOGRAPHS ↗");
    guide.href="https://github.com/Legioniz/toki-satsuei/blob/main/media-library/README.md";
    guide.target="_blank";
    guide.rel="noopener noreferrer";
    empty.append(guide);
  }else{
    const back=element("button","archive-empty-action","VIEW ALL COLLECTIONS");
    back.type="button";
    back.addEventListener("click",()=>{
      activeCategory="all";
      updateFilters();
      animateChange(groups,renderGroups);
      filters.querySelector('[data-category="all"]')?.focus({preventScroll:true});
    });
    empty.append(back);
  }
  groups.replaceChildren(empty);
}
function renderGroups(){
  const selected=activeCategory==="all"?archiveCategories:archiveCategories.filter(category=>category.id===activeCategory);
  const matching=selected.map(category=>{
    const albums=category.albums.filter(album=>{
      if(!activeQuery)return true;
      return normalize(category.title+" "+album.title+" "+(album.description||"")).includes(activeQuery);
    });
    return {...category,albums,image_count:albums.reduce((total,album)=>total+album.media.length,0)};
  });
  const populated=matching.filter(category=>category.albums.length);
  groups.replaceChildren();
  setCount(populated);
  if(!populated.length){
    showEmpty(activeQuery?"No albums match “"+activeQuery+"”.":(selected[0]?"No "+selected[0].title.toLowerCase()+" albums yet.":"The archive is ready for its first frame."),activeQuery);
    return;
  }
  populated.forEach(category=>groups.append(makeCategoryGroup(category)));
  revealWithin(groups);
}
function updateDialogProgress(){
  const maxScroll=Math.max(0,mediaRail.scrollWidth-mediaRail.clientWidth);
  const progress=maxScroll?Math.min(1,mediaRail.scrollLeft/maxScroll):1;
  if(albumProgressBar)albumProgressBar.style.transform="scaleX("+Math.max(.04,progress)+")";
  if(dialogPosition){
    const frames=[...mediaRail.children];
    let active=0;
    const marker=mediaRail.getBoundingClientRect().left+mediaRail.clientWidth*.34;
    frames.forEach((frame,index)=>{if(frame.getBoundingClientRect().left<=marker)active=index;});
    dialogPosition.textContent=String(active+1).padStart(2,"0")+" / "+String(frames.length).padStart(2,"0");
  }
  const left=document.querySelector('[data-dialog-scroll="-1"]');
  const right=document.querySelector('[data-dialog-scroll="1"]');
  if(left)left.disabled=mediaRail.scrollLeft<=3;
  if(right)right.disabled=mediaRail.scrollLeft>=maxScroll-3;
}
function openAlbum(category,album){
  albumReturnFocus=document.activeElement instanceof HTMLElement?document.activeElement:null;
  activeAlbum={category,album};
  dialog.classList.toggle("album-dialog--cinematic",["cosplay","events"].includes(category.id));
  dialogTitle.textContent=album.title;
  dialogCategory.textContent=category.title.toUpperCase();
  dialogDescription.textContent=album.description||"A collection from the TOKI SATSUEI archive.";
  dialogCount.textContent=countWords(album.media.length,"FRAME","FRAMES");
  mediaRail.replaceChildren();
  album.media.forEach((item,index)=>{
    const figure=element("figure","album-frame");
    figure.style.setProperty("--frame-index",String(Math.min(index,12)));
    const stage=element("div","album-frame-media");
    if(item.type==="video"){
      const video=element("video");
      video.src=item.src;video.controls=true;video.preload="metadata";video.playsInline=true;
      video.setAttribute("aria-label",item.title||"Video "+(index+1));
      stage.append(video);
    }else{
      const image=element("img");
      image.draggable=false;
      image.src=item.src;image.alt=item.alt||item.title||"TOKI SATSUEI photograph";
      image.loading=index<2?"eager":"lazy";image.decoding="async";
      addImageFallback(image,stage);
      stage.append(image);
    }
    figure.append(stage,element("figcaption","",item.title||("FRAME "+String(index+1).padStart(2,"0"))));
    mediaRail.append(figure);
  });
  mediaRail.scrollLeft=0;
  dialog.showModal();
  dialog.classList.remove("is-opening");
  requestAnimationFrame(()=>dialog.classList.add("is-opening"));
  requestAnimationFrame(updateDialogProgress);
  closeDialog.focus();
}
function closeAlbum(){
  if(!dialog.open)return;
  if(window.TokiMotion?.closeDialog)window.TokiMotion.closeDialog(dialog);
  else dialog.close();
}
document.querySelectorAll("[data-dialog-scroll]").forEach(button=>{
  button.addEventListener("click",()=>scrollTrack(mediaRail,Number(button.dataset.dialogScroll)));
});
mediaRail.addEventListener("scroll",updateDialogProgress,{passive:true});
closeDialog.addEventListener("click",closeAlbum);
dialog.addEventListener("click",event=>{if(event.target===dialog)closeAlbum();});
dialog.addEventListener("cancel",event=>{event.preventDefault();closeAlbum();});
dialog.addEventListener("close",()=>{
  mediaRail.querySelectorAll("video").forEach(video=>{video.pause();video.currentTime=0;});
  dialog.classList.remove("is-opening","album-dialog--cinematic");
  activeAlbum=null;
  if(albumReturnFocus?.isConnected)albumReturnFocus.focus({preventScroll:true});
  albumReturnFocus=null;
});
document.addEventListener("keydown",event=>{
  if(dialog.open){
    if(event.key==="ArrowRight"){event.preventDefault();scrollTrack(mediaRail,1);}
    else if(event.key==="ArrowLeft"){event.preventDefault();scrollTrack(mediaRail,-1);}
    else if(event.key==="Home"){event.preventDefault();mediaRail.scrollTo({left:0,behavior:reducedMotion?"auto":"smooth"});}
    else if(event.key==="End"){event.preventDefault();mediaRail.scrollTo({left:mediaRail.scrollWidth,behavior:reducedMotion?"auto":"smooth"});}
    return;
  }
  const active=document.activeElement;
  const editing=active instanceof HTMLElement&&(active.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName));
  if(event.key==="/"&&!event.ctrlKey&&!event.metaKey&&!event.altKey&&!editing){
    event.preventDefault();
    searchInput.focus();
  }
  if(event.key==="Escape"&&searchInput===document.activeElement&&searchInput.value){
    searchInput.value="";activeQuery="";renderGroups();
  }
});
searchInput.addEventListener("input",()=>{
  activeQuery=normalize(searchInput.value);
  animateChange(groups,renderGroups);
});
searchInput.addEventListener("keydown",event=>{
  if(event.key==="Escape"&&searchInput.value){
    searchInput.value="";activeQuery="";renderGroups();
  }
});
const year=document.querySelector("#year");
if(year)year.textContent=String(new Date().getFullYear());
async function loadArchive(){
  try{
    const response=await fetch("./media-library.json",{cache:"no-cache"});
    if(!response.ok)throw new Error("Archive index is not available yet.");
    const manifest=await response.json();
    archiveCategories=Array.isArray(manifest.categories)?manifest.categories:[];
    if(!archiveCategories.length)throw new Error("No archive categories were found.");
    archiveCategories.forEach(category=>{
      category.albums=Array.isArray(category.albums)?category.albums:[];
      category.image_count=Number(category.image_count||category.albums.reduce((total,album)=>total+(album.media||[]).length,0));
    });
    buildFilters();
    renderGroups();
    revealWithin(document);
  }catch(error){
    countLabel.textContent="ARCHIVE INDEX UNAVAILABLE";
    showEmpty("The archive is being prepared.");
  }
}
window.addEventListener("resize",()=>{if(dialog.open)requestAnimationFrame(updateDialogProgress);},{passive:true});
window.addEventListener("orientationchange",()=>{if(dialog.open)requestAnimationFrame(updateDialogProgress);},{passive:true});
loadArchive();

if(hasViewTransitions&&document.documentElement){
  document.documentElement.classList.add("supports-view-transitions");
}
