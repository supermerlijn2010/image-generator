# Image Generator Workspace

This repository contains two lightweight Streamlit applications that let you experiment with training and labeling image data using simple, local workflows.

## Folder 1 – Trainable Image Generator (`generator_app`)
* **Generate an image**: Enter a prompt to create a placeholder image that encodes the text into a colorized background. The image renders directly in the UI.
* **Train the image model**: Upload a ZIP archive of your own images and optional descriptions. The app extracts the files, stores them under `generator_app/data/training_runs/`, and saves metadata you can feed into a training backend.

Run the app:
```bash
pip install -r requirements.txt
streamlit run generator_app/app.py
```

## Folder 2 – Image Labeler (`labeler_app`)
* **Upload a data set**: Provide a ZIP file of images to load into the session.
* **Upload keywords**: Paste a comma-separated list of keywords to use during labeling.
* **Label images automatically**: Generates basic labels by matching keywords to filenames and saves them to JSON.
* **Train a model manually**: Walks through the dataset, lets you assign keywords per image, and saves labeled data for downstream training.

Run the app:
```bash
pip install -r requirements.txt
streamlit run labeler_app/app.py
```

## Dependencies
Both apps rely on [Streamlit](https://streamlit.io/) for the GUI and [Pillow](https://python-pillow.org/) for basic image handling. Install them with:
```bash
pip install -r requirements.txt
```
