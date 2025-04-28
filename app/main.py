from pathlib import Path
from datetime import datetime
import json, logging, os

from fastapi import FastAPI, Request
from fastapi.responses import (HTMLResponse, RedirectResponse,
                               JSONResponse, FileResponse)
from fastapi.templating import Jinja2Templates

from .tasks import generate_wordlist, celery_app
from .logconf import setup as setup_log

setup_log("INFO")
log = logging.getLogger("web")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

OUT_DIR = BASE_DIR / "outputs"
OUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Word-list Generator API")


def safe_stamp(label: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean = "".join(c for c in label if c.isalnum() or c in ("-", "_"))
    return f"{ts}_{clean or 'wordlist'}.txt"

def split_field(raw: str | None) -> list[str]:
    return [x for x in (raw or "").split() if x]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return TEMPLATES.TemplateResponse("index.html", {"request": request})

@app.post("/start")
async def start_task(request: Request):
    form = await request.form()
    label   = form.get("name_wordlist", "wordlist")
    outfile = safe_stamp(label)
    outpath = str(OUT_DIR / outfile)

    args = {
        "names":             split_field(form.get("names")),
        "year-from":         int(form.get("year-from")),
        "year-to":           int(form.get("year-to")),
        "tags":              split_field(form.get("tags")),
        "subconscious":      split_field(form.get("subconscious")),
        "temporal-spatial":  split_field(form.get("temporal-spatial")),
        "cultural-identity": split_field(form.get("cultural-identity")),
        "digital-rituals":   split_field(form.get("digital-rituals")),
        "psych-weak-spots":  split_field(form.get("psych-weak-spots")),
        "identity-layering": split_field(form.get("identity-layering")),
        "wifi-min":          int(form.get("wifi-min")),
        "wifi-max":          int(form.get("wifi-max")),
        "max-size-mb":       float(form.get("max-size-mb")),
        "mangling":          split_field(form.get("mangling")),
        "output":            outpath,
    }

    task = generate_wordlist.apply_async(
        kwargs={"form_data": {"cli_args_json": json.dumps(args)}})

    log.info("Queued task %s -> %s", task.id, outfile)
    return RedirectResponse(f"/progress/{task.id}", 303)

@app.get("/progress/{task_id}", response_class=HTMLResponse)
async def progress_page(request: Request, task_id: str):
    return TEMPLATES.TemplateResponse("progress.html",
                                      {"request": request, "task_id": task_id})

@app.get("/status/{task_id}")
async def status(task_id: str):
    res = celery_app.AsyncResult(task_id)
    if res.state == "PROGRESS":
        return JSONResponse({"state": "PROGRESS",
                             "pct": res.info.get("current", 0)})
    if res.state == "SUCCESS":
        return JSONResponse({"state": "SUCCESS", **res.result})
    return JSONResponse({"state": res.state})

@app.get("/download/{fname}")
async def download(fname: str):
    path = OUT_DIR / fname
    if not path.exists():
        return JSONResponse({"error": "file not found"}, 404)
    return FileResponse(path, filename=fname, media_type="text/plain")
