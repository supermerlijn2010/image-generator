import io
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "training_runs"
DATA_DIR.mkdir(parents=True, exist_ok=True)


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
    zip_path = temp_dir / upload.name
    zip_path.write_bytes(upload.getvalue())
    import zipfile

    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(temp_dir)
    return temp_dir


def show_generate_ui():
    st.header("Generate an image")
    prompt = st.text_input("Prompt", "A calm landscape at sunset")
    if st.button("Generate"):
        with st.spinner("Creating your image..."):
            image = _generate_placeholder_image(prompt)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            st.image(buffer.getvalue(), caption=f"Generated from: {prompt}")


def show_train_ui():
    st.header("Train with your images")
    uploaded_zip = st.file_uploader("Upload a ZIP file with images and descriptions", type=["zip"])
    keyword_text = st.text_area("List a few keywords (comma-separated)")
    desc_hint = "Use filenames as keys and short descriptions as values."
    description_json = st.text_area("Optional: JSON descriptions mapping filenames to text", help=desc_hint)

    if st.button("Start training"):
        if not uploaded_zip:
            st.error("Please upload a ZIP file to continue.")
            return

        with st.spinner("Processing your data..."):
            extracted = _extract_upload(uploaded_zip)
            keywords = [item.strip() for item in keyword_text.split(",") if item.strip()]
            descriptions: Dict[str, str] = {}
            if description_json:
                try:
                    descriptions = json.loads(description_json)
                except json.JSONDecodeError:
                    st.error("Could not parse the description JSON. Please fix the formatting.")
                    return

            run_dir = DATA_DIR / datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            run_dir.mkdir(parents=True, exist_ok=True)

            images_copied = 0
            for path in extracted.rglob("*"):
                if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
                    destination = run_dir / path.name
                    destination.write_bytes(path.read_bytes())
                    images_copied += 1

            _save_training_metadata(run_dir, keywords, descriptions)

        st.success(f"Training data prepared with {images_copied} images.")
        st.info("This example prepares data and metadata; plug your preferred training backend here.")


def main():
    st.set_page_config(page_title="Custom Image Generator", page_icon="🖼️")
    st.title("Folder 1 – Trainable Image Generator")

    mode = st.radio(
        "What do you want to do?",
        ["Generate a new image", "Train the image model"],
    )

    if mode == "Generate a new image":
        show_generate_ui()
    else:
        show_train_ui()


if __name__ == "__main__":
    main()
