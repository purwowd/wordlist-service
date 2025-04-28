import os, subprocess, json, logging
from celery import Celery
from celery.utils.log import get_task_logger
from .celery_config import BROKER_URL, BACKEND_URL
from .logconf import setup as setup_log

setup_log("INFO")
logger = get_task_logger("worker")

celery_app = Celery("wordlist_tasks", broker=BROKER_URL, backend=BACKEND_URL)

@celery_app.task(bind=True)
def generate_wordlist(self, form_data: dict):
    args_map = json.loads(form_data["cli_args_json"])
    out_file = args_map["output"]

    script = os.path.join(os.path.dirname(__file__), "wordlist_gen.py")
    cmd = ["python3", script]
    for k, v in args_map.items():
        flag = f"--{k}"
        if isinstance(v, list) and v:
            cmd.append(flag); cmd.extend(map(str, v))
        elif not isinstance(v, list):
            cmd.extend([flag, str(v)])

    logger.info("CLI args: %s", json.dumps(args_map))
    logger.info("Exec: %s", " ".join(cmd))

    with subprocess.Popen(cmd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True) as proc:
        for line in proc.stdout:
            line = line.rstrip()
            logger.info(line)
            if line.startswith("PROG"):
                try:
                    pct = int(line.split()[1])
                    self.update_state(state="PROGRESS",
                                      meta={"current": pct, "total": 100})
                except ValueError:
                    pass

    return {"download": f"/download/{os.path.basename(out_file)}"}
