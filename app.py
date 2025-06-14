# app.py
from __future__ import annotations
import io
import os
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, abort
from PIL import Image
import numpy as np

from dicom_utils import DicomController, load_dicom_images
from field_organization import get_field_manager
from settings import get_settings_manager

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Create language directory
LANG_DIR = BASE_DIR / "languages"
LANG_DIR.mkdir(exist_ok=True)

# Create settings directory
SETTINGS_DIR = BASE_DIR / "settings"
SETTINGS_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")

# Initialize managers on startup
field_manager = get_field_manager()
settings_manager = get_settings_manager()

# ─── helpers ────────────────────────────────────────────────────────────────

def frame_to_png_bytes(frame):
    """Convert a 2‑D numpy array to normalized PNG bytes."""
    # Ensure frame is numpy array
    if not isinstance(frame, np.ndarray):
        raise ValueError(f"Expected numpy array, got {type(frame)}")
    
    # Print debug info
    print(f"Converting frame: shape={frame.shape}, dtype={frame.dtype}, min={frame.min()}, max={frame.max()}")
    
    # Convert to float and normalize
    arr = frame.astype(float)
    arr_min = arr.min()
    arr_max = arr.max()
    
    if arr_max > arr_min:
        arr = (arr - arr_min) / (arr_max - arr_min) * 255
    else:
        arr = np.zeros_like(arr)
    
    # Convert to uint8
    arr = arr.astype(np.uint8)
    
    # If grayscale, ensure 2D array
    if arr.ndim == 2:
        img = Image.fromarray(arr, mode='L')  # Explicitly specify grayscale mode
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
    print(f"Found {len(files)} DICOM files in cache: {files[:5]}...")  # Print first 5 to avoid too long
    return jsonify(files)


@app.route("/api/cache/preview/<filename>")
def preview(filename):
    path = CACHE_DIR / filename
    print(f"Preview requested for: {filename}, exists: {path.exists()}")
    
    if not path.exists():
        abort(404)
    
    try:
        frames = load_dicom_images(path)
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
    
    # Use DicomController to get ordered metadata list
    controller = DicomController(path)
    metadata = controller.get_metadata()
    
    # Metadata is already a list of {"name": ..., "value": ...} dicts
    return jsonify(metadata)


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


@app.route("/api/language/<lang>", methods=["POST"])
def set_language(lang):
    """Set language."""
    settings_manager.language = lang
    return jsonify({"status": "ok", "language": lang})


@app.route("/api/language", methods=["GET"])
def get_language():
    """Get current language."""
    return jsonify({
        "current": settings_manager.language,
        "available": ["english", "chinese_simplified"]  # Hardcoded for now
    })


@app.route("/api/translations", methods=["GET"])
def get_translations():
    """Get current language's UI translations."""
    ui_keys = [
        "UI_APP_TITLE", "UI_IMPORT_FILE", "UI_IMPORT_FOLDER", "UI_SETTINGS",
        "UI_ATTRIBUTE", "UI_VALUE", "UI_SETTINGS_TITLE", "UI_OPTION1", "UI_OPTION2",
        "UI_LANGUAGE", "UI_CANCEL", "UI_SAVE", "UI_REMOVE", "UI_FILTER_SETTINGS",
        "UI_OK", "UI_SELECT_ALL", "UI_DESELECT_ALL"
    ]
    
    # Get fresh translations from field manager
    field_manager = get_field_manager()
    translations = {key: field_manager.translations.get(key, key) for key in ui_keys}
    return jsonify(translations)


@app.route("/api/filter/structure", methods=["GET"])
def get_filter_structure():
    """Get category and field structure for filter settings."""
    field_manager = get_field_manager()
    structure = field_manager.get_categories_with_fields()
    
    # Add visibility state from settings
    for category, data in structure.items():
        # Get category state
        field_indices = [f["index"] for f in data["fields"]]
        state = settings_manager.filter_settings.get_category_state(category, field_indices)
        data["state"] = state
        
        # Get field states
        for field in data["fields"]:
            field["visible"] = settings_manager.is_field_visible(field["index"])
    
    return jsonify(structure)


@app.route("/api/filter/settings", methods=["GET"])
def get_filter_settings():
    """Get current filter settings."""
    return jsonify({
        "categories": settings_manager.filter_settings.categories,
        "fields": settings_manager.filter_settings.fields
    })


@app.route("/api/filter/settings", methods=["POST"])
def update_filter_settings():
    """Update filter settings."""
    data = request.json
    categories = data.get("categories", {})
    fields = data.get("fields", {})
    
    settings_manager.update_filter_settings(categories, fields)
    
    # Notify field manager to update filtered definitions
    field_manager.notify_filter_update()
    
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5000)