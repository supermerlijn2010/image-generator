# Image Generator Workspace

This repository contains two lightweight Flask applications that let you experiment with training and labeling image data using simple, local workflows that run on any machine (no Streamlit required).

## Folder 1 – Trainable Image Generator (`generator_app`)
* **Generate an image**: Enter a prompt to create a placeholder image that encodes the text into a colorized background. The image renders directly in the UI and can be downloaded as two ZIPs: one for images and one for keywords (prompt text) that match the folder 1 training format.
* **Train the image model**: Upload two ZIP archives—one containing images (e.g., `image0001.png`) and one containing keyword text files with matching basenames (e.g., `image0001.txt`). The app extracts the files, aligns matching pairs, stores them under `generator_app/data/training_runs/`, and saves metadata indicating any missing keyword files.

Run the app locally:
```bash
pip install -r requirements.txt
python generator_app/app.py
# Open http://localhost:8000
```

Run it on a server for remote access (replace `SERVER_IP` with your machine's address). The default port is `8000`, but you can override it by setting `GENERATOR_PORT`:
```bash
pip install -r requirements.txt
# macOS/Linux/Git Bash/WSL
./scripts/run_generator_server.sh
# Windows Command Prompt/PowerShell
scripts\run_generator_server.bat
# Then visit http://SERVER_IP:8000 from your laptop
```

## Folder 2 – Image Labeler (`labeler_app`)
* **Upload a data set**: Provide a ZIP file of images to load into the session; you can download the same images back out as a training ZIP once loaded.
* **Upload keywords**: Paste a comma-separated list of keywords to use during labeling.
* **Label images automatically**: Generates basic labels by matching keywords to filenames and saves them to JSON.
* **Train a model manually**: Walks through the dataset, lets you assign keywords per image, and saves labeled data for downstream training.
* **Export for training**: Download two ZIPs—one containing the currently loaded images and one containing `.txt` files per image (keywords comma-separated)—ready to upload to the generator app's training flow.

Run the app locally:
```bash
pip install -r requirements.txt
python labeler_app/app.py
# Open http://localhost:8001
```

Run it on a server for remote access (default port `8001`; override with `LABELER_PORT`):
```bash
pip install -r requirements.txt
# macOS/Linux/Git Bash/WSL
./scripts/run_labeler_server.sh
# Windows Command Prompt/PowerShell
scripts\run_labeler_server.bat
# Then visit http://SERVER_IP:8001 from your laptop
```

## Dependencies
Both apps rely on [Flask](https://flask.palletsprojects.com/) for the GUI and [Pillow](https://python-pillow.org/) for basic image handling. Install them with:
```bash
pip install -r requirements.txt
```
