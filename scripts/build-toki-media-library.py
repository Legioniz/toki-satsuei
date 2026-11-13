#!/usr/bin/env python3
"""Build the public TOKI SATSUEI media archive manifest from upload folders."""
from __future__ import annotations
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
LIBRARY=ROOT/"media-library"
OUTPUT=ROOT/"media-library.json"
IMAGE_EXTENSIONS={".jpg",".jpeg",".png",".webp",".avif",".gif"}
VIDEO_EXTENSIONS={".mp4",".webm"}
MEDIA_EXTENSIONS=IMAGE_EXTENSIONS|VIDEO_EXTENSIONS
CATEGORY_INFO={
 "cosplay":("Cosplay","Character portraits, costumes, and the details that bring a concept to life.","01"),
 "portraits":("Portraits","Individual portraits made at an easy pace, with room for personality.","02"),
 "duo-groups":("Duo & groups","Shared frames, paired characters, and the people behind them.","03"),
 "events":("Events","Convention days, gatherings, performances, and moments in between.","04"),
 "casual-outdoor":("Casual & outdoor","Unhurried sessions in the places where memories happen.","05"),
 "behind-the-scenes":("Behind the camera","Setups, preparation, and the people making each frame.","06"),
}

def label(value:str)->str:
 value=re.sub(r"[-_]+"," ",value).strip()
 return re.sub(r"\s+"," ",value).title() or "Untitled album"

def sort_key(path:Path):
 return [(0,int(part)) if part.isdigit() else (1,part.casefold()) for part in re.split(r"(\d+)",path.name)]

def media_files(folder:Path)->list[Path]:
 if not folder.exists(): return []
 return sorted((path for path in folder.rglob("*") if path.is_file() and path.suffix.casefold() in MEDIA_EXTENSIONS and not any(part.startswith(".") for part in path.relative_to(folder).parts)),key=sort_key)

def media_record(path:Path,category_name:str,album_name:str)->dict:
 relative=path.relative_to(LIBRARY).as_posix()
 encoded="/".join(quote(part,safe="-._~") for part in relative.split("/"))
 title=label(path.stem)
 return {"type":"video" if path.suffix.casefold() in VIDEO_EXTENSIONS else "image","src":"./media-library/"+encoded,"title":title,"alt":f"{title} — {album_name}, {category_name}"}

def build_category(folder:Path)->dict:
 category_id=folder.name
 title,description,code=CATEGORY_INFO.get(category_id,(label(category_id),"A growing collection from the TOKI SATSUEI archive.","MORE"))
 albums=[]
 direct_files=sorted((path for path in folder.iterdir() if path.is_file() and path.suffix.casefold() in MEDIA_EXTENSIONS and not path.name.startswith(".")),key=sort_key)
 if direct_files:
  album_title="Latest uploads"
  albums.append({"id":category_id+"-latest-uploads","title":album_title,"description":"Recent additions to the "+title.lower()+" collection.","media":[media_record(path,title,album_title) for path in direct_files]})
 album_folders=sorted((path for path in folder.iterdir() if path.is_dir() and not path.name.startswith(".")),key=sort_key)
 for album_folder in album_folders:
  files=media_files(album_folder)
  if not files: continue
  album_title=label(album_folder.name)
  albums.append({"id":category_id+"-"+re.sub(r"[^a-z0-9]+","-",album_folder.name.casefold()).strip("-"),"title":album_title,"description":"A collection from the "+title.lower()+" archive.","media":[media_record(path,title,album_title) for path in files]})
 return {"id":category_id,"title":title,"description":description,"code":code,"album_count":len(albums),"image_count":sum(len(album["media"]) for album in albums),"albums":albums}

def main()->None:
 LIBRARY.mkdir(parents=True,exist_ok=True)
 folders={path.name:path for path in LIBRARY.iterdir() if path.is_dir() and not path.name.startswith(".")}
 order=list(CATEGORY_INFO)
 names=[name for name in order if name in folders]
 names.extend(sorted((name for name in folders if name not in CATEGORY_INFO),key=str.casefold))
 categories=[build_category(folders[name]) for name in names]
 manifest={"schema_version":1,"brand":"TOKI SATSUEI","categories":categories}
 OUTPUT.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 albums=sum(category["album_count"] for category in categories)
 frames=sum(category["image_count"] for category in categories)
 print(f"Built TOKI SATSUEI archive: {len(categories)} categories, {albums} albums, {frames} media files.")

if __name__=="__main__":
 main()
