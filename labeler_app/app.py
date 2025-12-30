import base64
import json
import os
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

from flask import Flask, flash, redirect, render_template_string, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}

app = Flask(__name__)
app.secret_key = os.environ.get("LABELER_APP_SECRET", "dev-secret-key")

APP_STATE: Dict[str, object] = {
    "images": [],  # List[Tuple[str, Path]]
    "keywords": [],  # List[str]
    "manual_labels": {},  # Dict[str, List[str]]
    "label_index": 0,
}


def _load_images_from_upload(upload) -> List[Tuple[str, Path]]:
    temp_dir = Path(tempfile.mkdtemp()) / "dataset"
    temp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = temp_dir / upload.filename
    upload.save(zip_path)

    images: List[Tuple[str, Path]] = []
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(temp_dir)
        for member in temp_dir.rglob("*"):
            if member.suffix.lower() in SUPPORTED_IMAGE_TYPES:
                images.append((member.name, member))
    return images


def _save_labels(name: str, labels: Dict[str, List[str]]) -> Path:
    output_dir = DATA_DIR / "labels"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{name}.json"
    output_path.write_text(json.dumps(labels, indent=2))
    return output_path


def _auto_label(images: List[Tuple[str, Path]], keywords: List[str]) -> Dict[str, List[str]]:
    labels: Dict[str, List[str]] = {}
    for filename, _ in images:
        matched = [kw for kw in keywords if kw.lower() in filename.lower()]
        labels[filename] = matched
    return labels


def reset_manual_labels():
    APP_STATE["manual_labels"] = {}
    APP_STATE["label_index"] = 0


@app.route("/upload-dataset", methods=["POST"])
def upload_dataset():
    upload = request.files.get("dataset")
    if not upload or upload.filename == "":
        flash("Please choose a ZIP file.", "error")
        return redirect(url_for("index"))
    try:
        APP_STATE["images"] = _load_images_from_upload(upload)
    except zipfile.BadZipFile:
        flash("Could not read that ZIP file. Please try again.", "error")
        return redirect(url_for("index"))
    reset_manual_labels()
    flash(f"Loaded {len(APP_STATE['images'])} images.", "success")
    return redirect(url_for("index"))


@app.route("/upload-keywords", methods=["POST"])
def upload_keywords():
    keywords_text = request.form.get("keywords", "")
    keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
    APP_STATE["keywords"] = keywords
    flash(f"Stored {len(keywords)} keywords.", "success")
    return redirect(url_for("index"))


@app.route("/auto-label", methods=["POST"])
def auto_label():
    images = APP_STATE.get("images", [])
    keywords = APP_STATE.get("keywords", [])
    if not images or not keywords:
        flash("Upload a dataset and keywords before running auto labeling.", "error")
        return redirect(url_for("index"))
    labels = _auto_label(images, keywords)
    output = _save_labels("auto-labels", labels)
    flash(f"Auto labels saved to {output}", "success")
    APP_STATE["manual_labels"] = labels.copy()
    return redirect(url_for("index"))


@app.route("/label", methods=["POST"])
def label_image():
    images: List[Tuple[str, Path]] = APP_STATE.get("images", [])
    keywords: List[str] = APP_STATE.get("keywords", [])
    index = APP_STATE.get("label_index", 0)

    if not images:
        flash("Upload a dataset first.", "error")
        return redirect(url_for("index"))
    if not keywords:
        flash("Add your keyword list to continue.", "error")
        return redirect(url_for("index"))
    if index >= len(images):
        flash("All images are already labeled.", "success")
        return redirect(url_for("index"))

    selections = request.form.getlist("labels")
    filename, _ = images[index]
    APP_STATE.setdefault("manual_labels", {})[filename] = selections
    APP_STATE["label_index"] = index + 1

    if APP_STATE["label_index"] >= len(images):
        output = _save_labels("manual-labels", APP_STATE.get("manual_labels", {}))
        flash(f"Saved labels to {output}. Connect your training backend to continue.", "success")
        return redirect(url_for("index"))

    return redirect(url_for("index"))


@app.route("/")
def index():
    images: List[Tuple[str, Path]] = APP_STATE.get("images", [])
    keywords: List[str] = APP_STATE.get("keywords", [])
    index = APP_STATE.get("label_index", 0)
    current_image: Tuple[str, str] | None = None

    if images and index < len(images):
        filename, path = images[index]
        try:
            image_bytes = path.read_bytes()
            encoded = base64.b64encode(image_bytes).decode("ascii")
            ext = path.suffix.lstrip(".").lower() or "png"
            mime = f"image/{ext}"
            data_uri = f"data:{mime};base64,{encoded}"
        except Exception:
            data_uri = None
        current_image = (filename, str(path))
    else:
        data_uri = None

    return render_template_string(
        TEMPLATE,
        image_count=len(images),
        keyword_count=len(keywords),
        current_index=index,
        keywords=keywords,
        current_image=current_image,
        image_data_uri=data_uri,
        manual_complete=images and index >= len(images),
    )


TEMPLATE = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <title>Image Labeling Assistant</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; max-width: 1000px; }
    .section { border: 1px solid #ddd; padding: 1rem; margin-bottom: 1.5rem; border-radius: 8px; }
    label { display: block; margin-top: 0.5rem; font-weight: bold; }
    input[type=text], textarea { width: 100%; padding: 0.5rem; margin-top: 0.25rem; }
    button { margin-top: 0.75rem; padding: 0.5rem 1rem; }
    img { max-width: 100%; margin-top: 0.75rem; border-radius: 6px; border: 1px solid #ccc; }
    .messages { margin: 0.5rem 0; padding: 0.75rem; border-radius: 6px; }
    .success { background: #e7f7ed; color: #1d7a43; border: 1px solid #9fd5b4; }
    .error { background: #fdecea; color: #b7221b; border: 1px solid #f5c2c0; }
  </style>
</head>
<body>
  <h1>Folder 2 – Image Labeler</h1>
  <p>Upload datasets, set keywords, auto-label, or walk through images to assign labels manually.</p>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
        <div class=\"messages {{ category }}\">{{ message }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  <div class=\"section\">
    <h2>1. Upload a data set</h2>
    <form method=\"post\" action=\"{{ url_for('upload_dataset') }}\" enctype=\"multipart/form-data\">
      <label for=\"dataset\">ZIP file of images</label>
      <input type=\"file\" id=\"dataset\" name=\"dataset\" accept=\".zip\" />
      <button type=\"submit\">Load images</button>
      <p>Loaded images: {{ image_count }}</p>
    </form>
  </div>

  <div class=\"section\">
    <h2>2. Upload keywords</h2>
    <form method=\"post\" action=\"{{ url_for('upload_keywords') }}\">
      <label for=\"keywords\">Comma-separated keyword list</label>
      <textarea id=\"keywords\" name=\"keywords\" rows=\"3\" placeholder=\"dark hair, red hair, bald\"></textarea>
      <button type=\"submit\">Save keywords</button>
      <p>Stored keywords: {{ keyword_count }}</p>
    </form>
  </div>

  <div class=\"section\">
    <h2>3. Label images automatically</h2>
    <form method=\"post\" action=\"{{ url_for('auto_label') }}\">
      <button type=\"submit\">Run auto labeling</button>
    </form>
  </div>

  <div class=\"section\">
    <h2>4. Train a model (manual labeling)</h2>
    {% if image_data_uri %}
      <p>Image {{ current_index + 1 }} of {{ image_count }}</p>
      <img src=\"{{ image_data_uri }}\" alt=\"Current image\" />
      <form method=\"post\" action=\"{{ url_for('label_image') }}\">
        <p>Select all matching keywords:</p>
        {% for kw in keywords %}
          <label><input type=\"checkbox\" name=\"labels\" value=\"{{ kw }}\" /> {{ kw }}</label>
        {% endfor %}
        <button type=\"submit\">Save and next</button>
      </form>
    {% elif manual_complete %}
      <p>All images labeled! Labels saved to the most recent output file.</p>
    {% else %}
      <p>Upload a dataset and keywords to begin manual labeling.</p>
    {% endif %}
  </div>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.environ.get("LABELER_PORT", "8001"))
    app.run(host="0.0.0.0", port=port, debug=False)
