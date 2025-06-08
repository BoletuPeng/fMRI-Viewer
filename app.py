# app.py
from __future__ import annotations
import io
import os
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, abort
from PIL import Image
import numpy as np

from dicom_utils import load_dicom, load_dicom_images

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")

# ─── helpers ────────────────────────────────────────────────────────────────

def frame_to_png_bytes(frame):
    """Convert a 2‑D numpy array to normalized PNG bytes."""
    # 确保frame是numpy数组
    if not isinstance(frame, np.ndarray):
        raise ValueError(f"Expected numpy array, got {type(frame)}")
    
    # 打印调试信息
    print(f"Converting frame: shape={frame.shape}, dtype={frame.dtype}, min={frame.min()}, max={frame.max()}")
    
    # 转换为float并归一化
    arr = frame.astype(float)
    arr_min = arr.min()
    arr_max = arr.max()
    
    if arr_max > arr_min:
        arr = (arr - arr_min) / (arr_max - arr_min) * 255
    else:
        arr = np.zeros_like(arr)
    
    # 转换为uint8
    arr = arr.astype(np.uint8)
    
    # 如果是灰度图，确保是2D数组
    if arr.ndim == 2:
        img = Image.fromarray(arr, mode='L')  # 明确指定灰度模式
    else:
        raise ValueError(f"Unexpected array dimensions: {arr.ndim}")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()

# ─── routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/cache/list")
def list_cache():
    files = [p.name for p in CACHE_DIR.glob("*.dcm")]
    print(f"Found {len(files)} DICOM files in cache: {files[:5]}...")  # 只打印前5个避免太长
    return jsonify(files)


@app.route("/api/cache/preview/<filename>")
def preview(filename):
    path = CACHE_DIR / filename
    print(f"Preview requested for: {filename}, exists: {path.exists()}")
    
    if not path.exists():
        abort(404)
    
    try:
        from dicom_utils import load_dicom_images
        frames = load_dicom_images(path)  # ← 改为只调用 load_dicom_images，不解读元数据
        print(f"Loaded DICOM images only: {len(frames)} frames")
        
        if not frames:
            print("No frames found in DICOM file")
            abort(415)  # Unsupported Media
        
        png_data = frame_to_png_bytes(frames[0])
        print(f"Generated PNG: {len(png_data)} bytes")
        
        return send_file(io.BytesIO(png_data), mimetype="image/png")
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        import traceback
        traceback.print_exc()
        abort(500)


@app.route("/api/cache/metadata/<filename>")
def meta(filename):
    path = CACHE_DIR / filename
    if not path.exists():
        abort(404)
    meta, _ = load_dicom(path)
    return jsonify(meta)


@app.route("/api/cache/delete/<filename>", methods=["DELETE"])
def delete(filename):
    f = CACHE_DIR / filename
    if f.exists():
        f.unlink()
    return ("", 204)


@app.route("/api/import", methods=["POST"])
def import_files():
    files = request.files.getlist("files[]")
    added = []
    for f in files:
        if not f.filename.lower().endswith(".dcm"):
            continue
        dest = CACHE_DIR / Path(f.filename).name
        f.save(dest)
        added.append(dest.name)
    return jsonify(added)


if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5000)