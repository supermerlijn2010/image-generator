import base64
import io
import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from flask import Flask, flash, redirect, render_template_string, request, send_file, url_for
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "training_runs"
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("GENERATOR_APP_SECRET", "dev-secret-key")


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
    uploaded_zip = request.files.get("dataset")
    keyword_text = request.form.get("keywords", "")
    description_json = request.form.get("descriptions", "")

    if not uploaded_zip or uploaded_zip.filename == "":
        flash("Upload a ZIP file to start training.", "error")
        return redirect(url_for("index"))

    try:
        extracted = _extract_upload(uploaded_zip)
    except zipfile.BadZipFile:
        flash("Could not read that ZIP file. Please re-upload.", "error")
        return redirect(url_for("index"))

    keywords = [item.strip() for item in keyword_text.split(",") if item.strip()]
    descriptions: Dict[str, str] = {}
    if description_json:
        try:
            descriptions = json.loads(description_json)
        except json.JSONDecodeError:
            flash("Descriptions JSON could not be parsed. Check the formatting.", "error")
            return redirect(url_for("index"))

    run_dir = DATA_DIR / datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    images_copied = 0
    for path in extracted.rglob("*"):
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
            destination = run_dir / path.name
            destination.write_bytes(path.read_bytes())
            images_copied += 1

    _save_training_metadata(run_dir, keywords, descriptions)
    message = f"Training data prepared with {images_copied} images. Data stored at {run_dir}."
    flash(message, "success")
    return render_template_string(TEMPLATE, generated_image=None, prompt=None, train_status=message)


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
    {% endif %}
  </div>

  <div class=\"section\">
    <h2>Option 2: Train the image model</h2>
    <form method=\"post\" action=\"{{ url_for('train_model') }}\" enctype=\"multipart/form-data\">
      <label for=\"dataset\">Upload a ZIP file with images</label>
      <input type=\"file\" id=\"dataset\" name=\"dataset\" accept=\".zip\" />

      <label for=\"keywords\">Keywords (comma-separated)</label>
      <textarea id=\"keywords\" name=\"keywords\" rows=\"2\" placeholder=\"sunset, portrait, abstract\"></textarea>

      <label for=\"descriptions\">Optional: JSON mapping of filenames to descriptions</label>
      <textarea id=\"descriptions\" name=\"descriptions\" rows=\"4\" placeholder=\"{\"image1.png\": \"A red flower\"}\"></textarea>

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
