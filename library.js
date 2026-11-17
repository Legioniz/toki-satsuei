(() => {
  "use strict";

const filters=document.querySelector("#library-filters");
const toolbar=document.querySelector(".library-toolbar");
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
const SVG_NS="http://www.w3.org/2000/svg";
let archiveCategories=[];
let activeCategory="all";
let activeQuery="";
let activeAlbum=null;
let albumReturnFocus=null;
let reducedMotion=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const motionPreference=window.matchMedia("(prefers-reduced-motion: reduce)");
motionPreference.addEventListener?.("change",event=>{reducedMotion=event.matches;});
const hasViewTransitions=typeof document.startViewTransition==="function";

function element(tag,className,text){
  const node=document.createElement(tag);
  if(className)node.className=className;
  if(text!==undefined)node.textContent=text;
  return node;
}
function countWords(count,singular,plural){return count+" "+(count===1?singular:plural);}
function normalize(value){return String(value||"").toLocaleLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"").trim();}
function safePlay(video){
  const promise=video.play();
  if(promise&&typeof promise.catch==="function")promise.catch(()=>{});
}
/* Move the album viewer by exactly one frame. */
function stepFrames(direction){
  mediaRail.scrollBy({left:mediaRail.clientWidth*direction,behavior:reducedMotion?"auto":"smooth"});
}

/* The red grease-pencil loop drawn around a frame. One loose, overshooting oval. */
function pencilMark(){
  const svg=document.createElementNS(SVG_NS,"svg");
  svg.setAttribute("class","pencil-mark");
  svg.setAttribute("viewBox","0 0 150 100");
  svg.setAttribute("preserveAspectRatio","none");
  svg.setAttribute("aria-hidden","true");
  svg.setAttribute("focusable","false");
  const path=document.createElementNS(SVG_NS,"path");
  path.setAttribute("pathLength","1");
  path.setAttribute("d","M13 54 C9 24 39 7 78 6 C118 5 144 17 142 48 C141 80 111 94 70 94 C31 94 6 79 9 41 C10 22 33 10 61 6");
  svg.append(path);
  return svg;
}

const activeTransitions=new WeakMap();
function animateChange(node,render){
  if(!node){render();return;}
  if(reducedMotion||!node.animate){render();return;}
  const token=(activeTransitions.get(node)?.token||0)+1;
  activeTransitions.set(node,{token,animation:null});
  const fade=node.animate([{opacity:1},{opacity:0}],{duration:110,easing:"ease-in"});
  activeTransitions.set(node,{token,animation:fade});
  fade.finished.then(()=>{
    if(activeTransitions.get(node)?.token!==token)return;
    render();
    const entrance=node.animate([{opacity:0},{opacity:1}],{duration:200,easing:"cubic-bezier(.2,.7,.2,1)"});
    activeTransitions.set(node,{token,animation:entrance});
  }).catch(()=>{});
}
function setCount(visibleCategories){
  const albums=visibleCategories.reduce((sum,category)=>sum+category.albums.length,0);
  const mediaItems=visibleCategories.reduce((sum,category)=>sum+category.albums.reduce((total,album)=>total+album.media.length,0),0);
  countLabel.textContent=countWords(albums,"album","albums")+" / "+countWords(mediaItems,"media item","media items");
}
function updateFilters(){
  filters.querySelectorAll("button").forEach(button=>{
    button.setAttribute("aria-pressed",String(button.dataset.category===activeCategory));
  });
}
function buildFilters(){
  filters.replaceChildren();
  const populatedCategories=archiveCategories.filter(category=>category.albums.length>0);
  const totalAlbums=populatedCategories.reduce((sum,category)=>sum+category.albums.length,0);
  const definitions=populatedCategories.length
    ?[{id:"all",title:"All albums",count:totalAlbums}].concat(populatedCategories.map(category=>({id:category.id,title:category.title,count:category.albums.length})))
    :[];
  definitions.forEach(item=>{
    const button=element("button","library-filter");
    button.type="button";
    button.dataset.category=item.id;
    button.setAttribute("aria-pressed",String(item.id===activeCategory));
    button.append(element("span","library-filter-name",item.title),element("span","library-filter-count",String(item.count)));
    button.addEventListener("click",()=>{
      if(activeCategory===item.id)return;
      activeCategory=item.id;
      updateFilters();
      animateChange(groups,renderGroups);
    });
    filters.append(button);
  });
}
function addImageFallback(image,container){
  image.addEventListener("error",()=>{
    image.remove();
    container.classList.add("media-unavailable");
    if(!container.querySelector(".media-fallback"))container.append(element("span","media-fallback","Frame unavailable"));
  },{once:true});
  image.addEventListener("load",()=>image.classList.add("is-loaded"),{once:true});
}
function makeAlbumCard(category,album){
  const button=element("button","album-card");
  button.type="button";
  button.setAttribute("aria-label","Open album "+album.title+" in "+category.title);
  const wrap=element("span","album-cover-wrap");
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
    cover.append(video,element("span","album-cover-type","Video"));
    button.addEventListener("pointerenter",()=>{if(!reducedMotion)safePlay(video);});
    button.addEventListener("pointerleave",()=>{video.pause();video.currentTime=0;});
    button.addEventListener("focus",()=>{if(!reducedMotion)safePlay(video);});
    button.addEventListener("blur",()=>{video.pause();video.currentTime=0;});
  }else{
    cover.append(element("span","album-cover-mark","時"));
  }
  wrap.append(cover,pencilMark());
  const meta=element("span","album-card-meta");
  meta.append(
    element("strong","album-card-title",album.title),
    element("small","album-card-count",countWords(album.media.length,"item","items"))
  );
  button.append(wrap,meta);
  button.addEventListener("click",()=>openAlbum(category,album));
  return button;
}
function makeCategoryGroup(category){
  const section=element("section","archive-group");
  const head=element("div","archive-group-head archive-group-copy-row");
  const copy=element("div","archive-group-copy");
  copy.append(
    element("h2","archive-group-title",category.title),
    element("p","archive-group-description",category.description||"A collection of moments worth keeping.")
  );
  head.append(copy,element("span","archive-group-meta",countWords(category.albums.length,"album","albums")+", "+countWords(category.media_count,"item","items")));
  const sheet=element("div","album-sheet");
  category.albums.forEach(album=>sheet.append(makeAlbumCard(category,album)));
  section.append(head,sheet);
  return section;
}
function makeProofSheet(){
  const sheet=element("div","proof-sheet");
  sheet.setAttribute("aria-hidden","true");
  const strip=element("div","proof-strip");
  for(let index=0;index<4;index+=1){
    const frame=element("span","proof-frame"+(index===3?" is-marked":""));
    if(index===3)frame.append(pencilMark());
    strip.append(frame);
  }
  sheet.append(strip,element("span","proof-note","first albums on the way"));
  return sheet;
}
function showEmpty(message,query="",descriptionOverride=""){
  const empty=element("section","archive-empty");
  const currentCategory=archiveCategories.find(category=>category.id===activeCategory);
  const hasAnyAlbums=archiveCategories.some(category=>category.albums.length>0);
  const copy=element("div","archive-empty-copy");
  const heading=element("h2","",message);
  const description=element("p","",descriptionOverride||(query
    ?"Try another title, or clear the search to browse every album."
    :currentCategory
      ?currentCategory.description+" New albums will appear here when available."
      :"Browse selected practice and detail studies on our homepage. New client albums appear here only with permission from the people featured."));
  copy.append(heading,description);
  if(!hasAnyAlbums&&!query)empty.append(makeProofSheet());
  empty.append(copy);

  if(query){
    const clear=element("button","archive-empty-action","Clear search");
    clear.type="button";
    clear.addEventListener("click",()=>{
      searchInput.value="";
      activeQuery="";
      renderGroups();
      searchInput.focus();
    });
    copy.append(clear);
  }else if(!hasAnyAlbums){
    const actions=element("div","archive-empty-actions");
    const studies=element("a","archive-upload-guide","See selected frames");
    studies.href="./index.html#work";
    const sessions=element("a","archive-upload-guide","Explore sessions");
    sessions.href="./index.html#sessions";
    actions.append(studies,sessions);
    copy.append(actions);
  }else{
    const back=element("button","archive-empty-action","View all albums");
    back.type="button";
    back.addEventListener("click",()=>{
      activeCategory="all";
      updateFilters();
      animateChange(groups,renderGroups);
      filters.querySelector('[data-category="all"]')?.focus({preventScroll:true});
    });
    copy.append(back);
  }
  groups.replaceChildren(empty);
}
function renderGroups(){
  const hasPublicAlbums=archiveCategories.some(category=>category.albums.length>0);
  if(toolbar){toolbar.classList.toggle("is-empty",!hasPublicAlbums);toolbar.classList.remove("is-loading");}
  const selected=activeCategory==="all"?archiveCategories.filter(category=>category.albums.length>0):archiveCategories.filter(category=>category.id===activeCategory);
  const matching=selected.map(category=>{
    const albums=category.albums.filter(album=>{
      if(!activeQuery)return true;
      return normalize(category.title+" "+album.title+" "+(album.description||"")).includes(activeQuery);
    });
    const media=albums.flatMap(album=>album.media);
    return {...category,albums,media_count:media.length,image_count:media.filter(item=>item.type==="image").length,video_count:media.filter(item=>item.type==="video").length};
  });
  const populated=matching.filter(category=>category.albums.length);
  groups.replaceChildren();
  setCount(populated);
  if(!populated.length){
    if(!hasPublicAlbums&&!activeQuery){
      showEmpty("The public archive is being prepared.","","Browse our selected practice and detail studies on the homepage. New client albums will appear here only with permission from the people featured.");
    }else{
      showEmpty(activeQuery?"No albums match “"+activeQuery+"”.":(selected[0]?"No "+selected[0].title.toLowerCase()+" albums yet.":"No public albums are available yet."),activeQuery);
    }
    return;
  }
  populated.forEach(category=>groups.append(makeCategoryGroup(category)));
  groups.append(element("p","archive-footnote","Client albums appear here only with permission from the people featured."));
}
function updateDialogProgress(){
  const maxScroll=Math.max(0,mediaRail.scrollWidth-mediaRail.clientWidth);
  const progress=maxScroll?Math.min(1,mediaRail.scrollLeft/maxScroll):1;
  if(albumProgressBar)albumProgressBar.style.transform="scaleX("+Math.max(.04,progress)+")";
  if(dialogPosition){
    const frames=[...mediaRail.children];
    let active=0;
    const marker=mediaRail.getBoundingClientRect().left+mediaRail.clientWidth*.5;
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
  dialogTitle.textContent=album.title;
  dialogCategory.textContent=category.title;
  dialogDescription.textContent=album.description||"A collection from the TOKI SATSUEI archive.";
  dialogCount.textContent=countWords(album.media.length,"item","items");
  mediaRail.replaceChildren();
  album.media.forEach((item,index)=>{
    const figure=element("figure","album-frame");
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
    figure.append(stage,element("figcaption","",item.title||("Frame "+(index+1))));
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
  button.addEventListener("click",()=>stepFrames(Number(button.dataset.dialogScroll)));
});
mediaRail.addEventListener("scroll",updateDialogProgress,{passive:true});
closeDialog.addEventListener("click",closeAlbum);
dialog.addEventListener("cancel",event=>{event.preventDefault();closeAlbum();});
dialog.addEventListener("close",()=>{
  mediaRail.querySelectorAll("video").forEach(video=>{video.pause();video.currentTime=0;});
  dialog.classList.remove("is-opening");
  activeAlbum=null;
  if(albumReturnFocus?.isConnected)albumReturnFocus.focus({preventScroll:true});
  albumReturnFocus=null;
});
document.addEventListener("keydown",event=>{
  if(dialog.open){
    if(event.key==="ArrowRight"){event.preventDefault();stepFrames(1);}
    else if(event.key==="ArrowLeft"){event.preventDefault();stepFrames(-1);}
    else if(event.key==="Home"){event.preventDefault();mediaRail.scrollTo({left:0,behavior:reducedMotion?"auto":"smooth"});}
    else if(event.key==="End"){event.preventDefault();mediaRail.scrollTo({left:mediaRail.scrollWidth,behavior:reducedMotion?"auto":"smooth"});}
    return;
  }
  const active=document.activeElement;
  const editing=active instanceof HTMLElement&&(active.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName));
  if(event.key==="/"&&!toolbar?.classList.contains("is-empty")&&!event.ctrlKey&&!event.metaKey&&!event.altKey&&!editing){
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
      const media=category.albums.flatMap(album=>Array.isArray(album.media)?album.media:[]);
      const imageCount=media.filter(item=>item.type==="image").length;
      const videoCount=media.filter(item=>item.type==="video").length;
      category.album_count=Number.isFinite(Number(category.album_count))?Number(category.album_count):category.albums.length;
      category.image_count=Number.isFinite(Number(category.image_count))?Number(category.image_count):imageCount;
      category.video_count=Number.isFinite(Number(category.video_count))?Number(category.video_count):videoCount;
      category.media_count=Number.isFinite(Number(category.media_count))?Number(category.media_count):media.length;
    });
    buildFilters();
    renderGroups();
  }catch(error){
    countLabel.textContent="Archive index unavailable";
    if(toolbar){toolbar.classList.add("is-empty");toolbar.classList.remove("is-loading");}
    showEmpty("The archive is temporarily unavailable.","","Please return later, or browse the selected practice frames on the homepage.");
  }
}
window.addEventListener("resize",()=>{if(dialog.open)requestAnimationFrame(updateDialogProgress);},{passive:true});
window.addEventListener("orientationchange",()=>{if(dialog.open)requestAnimationFrame(updateDialogProgress);},{passive:true});
loadArchive();

if(hasViewTransitions&&document.documentElement){
  document.documentElement.classList.add("supports-view-transitions");
}
})();
