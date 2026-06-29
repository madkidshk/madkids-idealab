#!/usr/bin/env python3
import cgi
import json
import os
import re
import shutil
import subprocess
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "3d_jobs"
REFINE_SCRIPT = ROOT / "3d_print_scripts" / "refine_rough_mesh.py"
SAMPLE_STL = ROOT / "3d_print_assets" / "fairwood_mascot_round_v1.stl"
BLENDER = os.environ.get("BLENDER_BIN", "/opt/homebrew/bin/blender")
GEMMA_MODEL = os.environ.get("GEMMA_MODEL", "gemma4:12b")


def safe_name(name):
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
    return cleaned[:120] or "upload"


def write_upload(field, folder, fallback):
    if field is None or not getattr(field, "filename", ""):
        return None
    path = folder / safe_name(field.filename or fallback)
    with path.open("wb") as fh:
        shutil.copyfileobj(field.file, fh)
    return path


def run_cmd(cmd, timeout):
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def clean_cli_text(text):
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text or "")
    text = re.sub(r"[\u2800-\u28ff]", "", text)
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    markers = ["1. 造型", "1 造型", "1.  造型"]
    starts = [text.find(marker) for marker in markers if text.find(marker) >= 0]
    if starts:
        text = text[min(starts):]
    return text.strip()


def gemma_plan(image_path, model_path, notes):
    prompt = f"""用廣東話，250字內。你係 MK Lab 3D print 建模顧問。

Reference: {image_path.name if image_path else "未提供"}
Rough mesh: {model_path.name if model_path else "未提供"}
要求: {notes or "四肢圓潤、有厚度，唔好扁平，輸出 STL。"}

只輸出四段：
1 造型修正
2 Blender參數 target_height_mm/solidify_mm/bevel_mm/voxel_size/smooth_iterations
3 3D print風險
4 人工檢查

不要推理過程。不要話自己可以生 mesh；Gemma只出方案，Blender做refine。
"""
    result = run_cmd(["ollama", "run", GEMMA_MODEL, prompt], timeout=300)
    if result["returncode"] != 0:
        return "Gemma failed:\n" + clean_cli_text(result["stderr"])
    return clean_cli_text(result["stdout"])


def refine_mesh(input_path, job_dir):
    output_path = job_dir / "refined_for_print.stl"
    report_path = job_dir / "printability_report.json"
    cmd = [
        BLENDER,
        "--background",
        "--python",
        str(REFINE_SCRIPT),
        "--",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--report",
        str(report_path),
        "--target-height-mm",
        "80",
        "--solidify-mm",
        "0",
        "--bevel-mm",
        "0.6",
        "--voxel-size",
        "0.9",
        "--smooth-iterations",
        "8",
    ]
    result = run_cmd(cmd, timeout=180)
    report = {}
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    return result, output_path, report_path, report


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def json_response(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/api/3d/plan-refine":
            self.json_response(404, {"ok": False, "error": "unknown endpoint"})
            return

        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                    "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
                },
            )
            job_id = time.strftime("%Y%m%d-%H%M%S")
            job_dir = JOBS / job_id
            job_dir.mkdir(parents=True, exist_ok=True)

            image_path = write_upload(form["image"] if "image" in form else None, job_dir, "reference.png")
            model_path = write_upload(form["model"] if "model" in form else None, job_dir, "rough.stl")
            if not model_path and form.getfirst("useSample") == "1":
                model_path = job_dir / SAMPLE_STL.name
                shutil.copy2(SAMPLE_STL, model_path)

            notes = form.getfirst("notes", "")
            if not model_path:
                self.json_response(400, {"ok": False, "error": "需要 rough 3D file；Gemma 不能單靠圖片直接輸出 STL。"})
                return

            plan = gemma_plan(image_path, model_path, notes)
            blender_result, output_path, report_path, report = refine_mesh(model_path, job_dir)
            ok = blender_result["returncode"] == 0 and output_path.exists()
            self.json_response(200 if ok else 500, {
                "ok": ok,
                "jobId": job_id,
                "plan": plan,
                "report": report,
                "outputUrl": f"/3d_jobs/{job_id}/{output_path.name}" if output_path.exists() else "",
                "reportUrl": f"/3d_jobs/{job_id}/{report_path.name}" if report_path.exists() else "",
                "blender": blender_result,
            })
        except subprocess.TimeoutExpired as err:
            self.json_response(504, {"ok": False, "error": f"timeout: {err}"})
        except Exception as err:
            self.json_response(500, {"ok": False, "error": str(err)})


def main():
    os.chdir(ROOT)
    JOBS.mkdir(exist_ok=True)
    port = int(os.environ.get("PORT", "8013"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"MK Lab 3D server: http://127.0.0.1:{port}/3d_gatekeep.html")
    server.serve_forever()


if __name__ == "__main__":
    main()
