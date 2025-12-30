import base64
import io
import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

from flask import Flask, flash, redirect, render_template_string, request, send_file, url_for
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "training_runs"
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("GENERATOR_APP_SECRET", "dev-secret-key")
LAST_GENERATED = {"prompt": None, "image_bytes": None, "filename": None}


def _seed_from_prompt(prompt: str) -> int:
    return sum(ord(char) for char in prompt) % 255 or 1


def _generate_placeholder_image(prompt: str) -> Image.Image:
    seed = _seed_from_prompt(prompt)
    width, height = 512, 512
    background = (seed, 255 - seed, (seed * 2) % 255)
    image = Image.new("RGB", (width, height), color=background)
    draw = ImageDraw.Draw(image)
    text = prompt[:50] if prompt else "Custom Image"
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    text_position = (20, height // 2 - 10)
    draw.text(text_position, text, fill=(255, 255, 255), font=font)
    return image


def _save_training_metadata(output_dir: Path, keywords: List[str], descriptions: Dict[str, str]) -> None:
    payload = {
        "keywords": keywords,
        "descriptions": descriptions,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(payload, indent=2))


def _extract_upload(upload) -> Path:
    temp_dir = Path(tempfile.mkdtemp())
    zip_path = temp_dir / upload.filename
    upload.save(zip_path)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(temp_dir)
    return temp_dir


def _collect_files(directory: Path, allowed_suffixes: Set[str]) -> List[Path]:
    files: List[Path] = []
    for path in directory.rglob("*"):
        if path.suffix.lower() in allowed_suffixes:
            files.append(path)
    return files


def _image_to_base64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@app.route("/generate", methods=["POST"])
def generate_image():
    prompt = request.form.get("prompt", "").strip()
    if not prompt:
        flash("Please provide a prompt to generate an image.", "error")
        return redirect(url_for("index"))

    image = _generate_placeholder_image(prompt)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"generated-{timestamp}.png"
    LAST_GENERATED.update({"prompt": prompt, "image_bytes": buffer.getvalue(), "filename": filename})
    encoded = _image_to_base64(image)
    flash("Image created below.", "success")
    return render_template_string(
        TEMPLATE,
        generated_image=encoded,
        prompt=prompt,
        train_status=None,
    )


@app.route("/train", methods=["POST"])
def train_model():
    images_zip = request.files.get("images_zip")
    keywords_zip = request.files.get("keywords_zip")

    if not images_zip or images_zip.filename == "":
        flash("Upload the images ZIP to start training.", "error")
        return redirect(url_for("index"))
    if not keywords_zip or keywords_zip.filename == "":
        flash("Upload the keywords ZIP to start training.", "error")
        return redirect(url_for("index"))

    try:
        images_dir = _extract_upload(images_zip)
        keywords_dir = _extract_upload(keywords_zip)
    except zipfile.BadZipFile:
        flash("Could not read one of the ZIP files. Please re-upload.", "error")
        return redirect(url_for("index"))

    image_files = _collect_files(images_dir, {".png", ".jpg", ".jpeg", ".bmp", ".gif"})
    keyword_files = _collect_files(keywords_dir, {".txt"})

    if not image_files:
        flash("No images found in the images ZIP.", "error")
        return redirect(url_for("index"))
    if not keyword_files:
        flash("No keyword text files found in the keywords ZIP.", "error")
        return redirect(url_for("index"))

    keyword_map = {path.stem: path for path in keyword_files}

    run_dir = DATA_DIR / datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    images_out = run_dir / "images"
    keywords_out = run_dir / "keywords"
    images_out.mkdir(parents=True, exist_ok=True)
    keywords_out.mkdir(parents=True, exist_ok=True)

    matched = 0
    missing = []
    for image_path in image_files:
        stem = image_path.stem
        dest_img = images_out / image_path.name
        dest_img.write_bytes(image_path.read_bytes())

        keyword_path = keyword_map.get(stem)
        if keyword_path:
            dest_kw = keywords_out / f"{stem}.txt"
            dest_kw.write_bytes(keyword_path.read_bytes())
            matched += 1
        else:
            missing.append(image_path.name)

    _save_training_metadata(run_dir, keywords=[], descriptions={"missing_keywords": missing})
    message = (
        f"Training data prepared. Images: {len(image_files)}, keyword files copied: {matched}. "
        f"Missing keyword files for {len(missing)} images. Data stored at {run_dir}."
    )
    flash(message, "success")
    return render_template_string(TEMPLATE, generated_image=None, prompt=None, train_status=message)


@app.route("/download/generated/images.zip")
def download_generated_images():
    if not LAST_GENERATED["image_bytes"]:
        flash("Generate an image first to download it.", "error")
        return redirect(url_for("index"))
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(LAST_GENERATED["filename"], LAST_GENERATED["image_bytes"])
    memory_file.seek(0)
    download_name = "generated-images.zip"
    return send_file(memory_file, as_attachment=True, download_name=download_name, mimetype="application/zip")


@app.route("/download/generated/keywords.zip")
def download_generated_keywords():
    if not LAST_GENERATED["image_bytes"] or not LAST_GENERATED["prompt"]:
        flash("Generate an image first to download keywords.", "error")
        return redirect(url_for("index"))
    stem = Path(LAST_GENERATED["filename"]).stem
    keyword_content = LAST_GENERATED["prompt"]
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{stem}.txt", keyword_content)
    memory_file.seek(0)
    download_name = "generated-keywords.zip"
    return send_file(memory_file, as_attachment=True, download_name=download_name, mimetype="application/zip")


@app.route("/")
def index():
    return render_template_string(TEMPLATE, generated_image=None, prompt=None, train_status=None)


TEMPLATE = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <title>Trainable Image Generator</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; max-width: 900px; }
    h1 { margin-bottom: 0.5rem; }
    .section { border: 1px solid #ddd; padding: 1rem; margin-bottom: 1.5rem; border-radius: 8px; }
    .messages { margin: 0.5rem 0; padding: 0.75rem; border-radius: 6px; }
    .success { background: #e7f7ed; color: #1d7a43; border: 1px solid #9fd5b4; }
    .error { background: #fdecea; color: #b7221b; border: 1px solid #f5c2c0; }
    label { display: block; margin-top: 0.5rem; font-weight: bold; }
    input[type=text], textarea { width: 100%; padding: 0.5rem; margin-top: 0.25rem; }
    button { margin-top: 0.75rem; padding: 0.5rem 1rem; }
    img { max-width: 100%; margin-top: 0.75rem; border-radius: 6px; border: 1px solid #ccc; }
  </style>
</head>
<body>
  <h1>Folder 1 – Trainable Image Generator</h1>
  <p>Use these lightweight forms to generate placeholder images or prepare your own data for training.</p>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
        <div class=\"messages {{ category }}\">{{ message }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  <div class=\"section\">
    <h2>Option 1: Generate an image</h2>
    <form method=\"post\" action=\"{{ url_for('generate_image') }}\">
      <label for=\"prompt\">Prompt</label>
      <input type=\"text\" id=\"prompt\" name=\"prompt\" value=\"{{ prompt or '' }}\" placeholder=\"A calm landscape at sunset\" />
      <button type=\"submit\">Generate</button>
    </form>
    {% if generated_image %}
      <img src=\"{{ generated_image }}\" alt=\"Generated image\" />
      <div style=\"margin-top:0.5rem;\">
        <a href=\"{{ url_for('download_generated_images') }}\">Download images ZIP</a>
        &nbsp;|&nbsp;
        <a href=\"{{ url_for('download_generated_keywords') }}\">Download keywords ZIP</a>
      </div>
    {% endif %}
  </div>

  <div class=\"section\">
    <h2>Option 2: Train the image model</h2>
    <form method=\"post\" action=\"{{ url_for('train_model') }}\" enctype=\"multipart/form-data\">
      <label for=\"images_zip\">Upload images ZIP (e.g., image0001.png)</label>
      <input type=\"file\" id=\"images_zip\" name=\"images_zip\" accept=\".zip\" />

      <label for=\"keywords_zip\">Upload keywords ZIP (matching .txt files, e.g., image0001.txt)</label>
      <input type=\"file\" id=\"keywords_zip\" name=\"keywords_zip\" accept=\".zip\" />

      <p style=\"color:#444;\">Keyword filenames should match images (image0001.png + image0001.txt).</p>
      <button type=\"submit\">Prepare training data</button>
    </form>
    {% if train_status %}
      <p>{{ train_status }}</p>
    {% endif %}
  </div>

  <p style=\"color:#666;\">The current implementation prepares and stores your data. Connect your preferred training backend to start fine-tuning.</p>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.environ.get("GENERATOR_PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
