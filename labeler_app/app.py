import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}


def _load_images_from_upload(upload) -> List[Tuple[str, Image.Image]]:
    temp_dir = Path(tempfile.mkdtemp()) / "dataset"
    temp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = temp_dir / upload.name
    zip_path.write_bytes(upload.getvalue())

    import zipfile

    images: List[Tuple[str, Image.Image]] = []
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(temp_dir)
        for member in temp_dir.rglob("*"):
            if member.suffix.lower() in SUPPORTED_IMAGE_TYPES:
                try:
                    images.append((member.name, Image.open(member).copy()))
                except Exception:
                    continue
    return images


def _save_labels(name: str, labels: Dict[str, List[str]]) -> Path:
    output_dir = DATA_DIR / "labels"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{name}.json"
    output_path.write_text(json.dumps(labels, indent=2))
    return output_path


def _auto_label(images: List[Tuple[str, Image.Image]], keywords: List[str]) -> Dict[str, List[str]]:
    labels: Dict[str, List[str]] = {}
    for filename, _ in images:
        matched = [kw for kw in keywords if kw.lower() in filename.lower()]
        labels[filename] = matched
    return labels


def ensure_state():
    st.session_state.setdefault("images", [])
    st.session_state.setdefault("keywords", [])
    st.session_state.setdefault("manual_labels", {})
    st.session_state.setdefault("label_index", 0)


def option_upload_dataset():
    st.subheader("1. Upload a data set")
    upload = st.file_uploader("Choose a ZIP with images", type=["zip"], key="dataset")
    if upload and st.button("Load images"):
        st.session_state["images"] = _load_images_from_upload(upload)
        st.session_state["label_index"] = 0
        st.session_state["manual_labels"] = {}
        st.success(f"Loaded {len(st.session_state['images'])} images.")


def option_upload_keywords():
    st.subheader("2. Upload keywords")
    keywords_text = st.text_area("Paste comma-separated keywords", key="keywords_text")
    if st.button("Save keywords"):
        keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
        st.session_state["keywords"] = keywords
        st.success(f"Stored {len(keywords)} keywords.")


def option_label_images():
    st.subheader("3. Label images automatically")
    if not st.session_state.get("images") or not st.session_state.get("keywords"):
        st.info("Upload a dataset and keywords first.")
        return
    if st.button("Run auto labeling"):
        labels = _auto_label(st.session_state["images"], st.session_state["keywords"])
        output = _save_labels("auto-labels", labels)
        st.success(f"Auto labels saved to {output}")
        st.json(labels)


def option_train_model():
    st.subheader("4. Train a model with manual labels")
    images = st.session_state.get("images", [])
    keywords = st.session_state.get("keywords", [])

    if not images:
        st.info("Upload a dataset first.")
        return
    if not keywords:
        st.info("Add your keyword list to continue.")
        return

    index = st.session_state.get("label_index", 0)
    if index >= len(images):
        st.success("All images labeled! Saving data...")
        output = _save_labels("manual-labels", st.session_state.get("manual_labels", {}))
        st.write(f"Saved labels to {output}")
        st.info("Connect your training backend here to fine-tune a model with these labels.")
        return

    filename, image = images[index]
    st.image(image, caption=filename)
    selections = st.multiselect("Select keywords for this image", keywords, key=f"select_{index}")

    if st.button("Save and next"):
        st.session_state.setdefault("manual_labels", {})[filename] = selections
        st.session_state["label_index"] = index + 1
        st.experimental_rerun()


def main():
    ensure_state()
    st.set_page_config(page_title="Image Labeling Assistant", page_icon="🏷️")
    st.title("Folder 2 – Image Labeler")

    option = st.radio(
        "Pick a task",
        [
            "Upload dataset",
            "Upload keywords",
            "Label images automatically",
            "Manual labeling and training",
        ],
    )

    if option == "Upload dataset":
        option_upload_dataset()
    elif option == "Upload keywords":
        option_upload_keywords()
    elif option == "Label images automatically":
        option_label_images()
    else:
        option_train_model()


if __name__ == "__main__":
    main()
