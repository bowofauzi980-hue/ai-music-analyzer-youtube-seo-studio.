# AI Music Analyzer & YouTube SEO Studio

A bilingual (English + Bahasa Indonesia) Streamlit starter app for:
- Reading public YouTube video metadata and embedding a video.
- Analyzing an authorized audio file for approximate tempo, key, energy, and timbre.
- Transcribing audio to text with Faster-Whisper and exporting TXT/SRT.
- Generating bilingual YouTube title, description, tags, hashtags, thumbnail text, and thumbnail prompts.
- Exporting the complete result as JSON.

## Important YouTube limitation

The YouTube URL is used for public metadata via YouTube's oEmbed endpoint and for embedding the video. This project **does not download or rip audio from YouTube**. To analyze audio or transcribe lyrics, upload a file that you own or have permission to process. This avoids building a workflow that bypasses YouTube's download restrictions or copyright protections.

## Features and limitations

- **Audio analysis:** `librosa` estimates tempo, a rough key candidate, energy, spectral brightness, and a heuristic mood. These are not professional-grade genre classification.
- **Transcription:** Faster-Whisper runs locally. Accuracy depends on vocal clarity, language, and background music. The first run downloads model weights; CPU processing can be slow.
- **SEO:** Uses templates and user-supplied metadata/keywords. It does not access YouTube search volume or guarantee ranking.
- **Free hosting:** Audio processing can exceed free hosting CPU/RAM limits. Start with metadata and SEO on free hosting; test audio features on a machine with enough memory.

## Project structure

```text
ai_music_analyzer_youtube_seo_studio/
├── app.py
├── requirements.txt
├── requirements-minimal.txt
├── packages.txt
├── .gitignore
├── .streamlit/
│   └── config.toml
└── README.md
```

## Run locally

Python 3.10 or 3.11 is recommended.

1. Install FFmpeg:
   - Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Windows: install FFmpeg and add it to PATH.
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate it:
   - Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`
4. Install packages:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Start:
   ```bash
   streamlit run app.py
   ```
6. Open the local URL shown in the terminal (usually `http://localhost:8501`).

For a lightweight metadata + SEO-only run:
```bash
pip install -r requirements-minimal.txt
streamlit run app.py
```
The audio-analysis buttons require the full dependencies.

## Publish to GitHub

1. Create a new repository on GitHub, e.g. `ai-music-analyzer-youtube-seo-studio`.
2. Do not upload private audio, API keys, `.env`, or `secrets.toml`.
3. From this project folder:
   ```bash
   git init
   git add .
   git commit -m "Initial AI Music Analyzer and YouTube SEO Studio"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/ai-music-analyzer-youtube-seo-studio.git
   git push -u origin main
   ```

## Deploy to Streamlit Community Cloud

1. Push the repository to GitHub.
2. Sign in to Streamlit Community Cloud and create an app from the repository.
3. Select branch `main`, main file `app.py`, and deploy.
4. If the deployment build supports apt packages, `packages.txt` requests FFmpeg.
5. If full dependencies fail or exceed available resources, switch to `requirements-minimal.txt` (rename it to `requirements.txt` for the deployment) and deploy metadata + SEO features only.

Free hosting limits change over time and may not support reliable transcription of long songs. For long audio, run locally or use a suitable CPU/GPU server.

## Configuration and secrets

This starter project does not require API keys. YouTube metadata is fetched from the public oEmbed endpoint. No secrets should be committed.

If you later add a paid AI API, keep credentials in Streamlit secrets:
- Local: `.streamlit/secrets.toml` (already ignored by `.gitignore`)
- Hosted: enter the key in the host's Secrets settings.

Example only (do not add a real key to GitHub):
```toml
AI_PROVIDER_API_KEY = "put-your-key-here"
```
Read it in Python with `st.secrets["AI_PROVIDER_API_KEY"]`. Never hard-code API keys in `app.py`.

## Privacy

- Uploaded audio is processed by the app instance and temporary files are deleted after processing.
- The app does not intentionally save uploaded audio to a project folder.
- On a hosted deployment, files are processed on the host's server; do not upload sensitive or unauthorized audio.
- For privacy-sensitive work, run locally.

## Troubleshooting

- **FFmpeg missing:** install FFmpeg and confirm `ffmpeg -version` works.
- **Librosa import / audio decode errors:** check Python version, FFmpeg, and supported file type.
- **Transcription too slow:** try a shorter clip, use a smaller Whisper model, or run on a faster machine.
- **Out of memory:** deploy the metadata/SEO-only version or use a server with more RAM.
- **YouTube metadata unavailable:** the video may be private, restricted, or the URL may be malformed.

## Responsible use

Only process audio you own or are authorized to use. Respect copyright, licenses, platform terms, privacy, and applicable law. Review generated metadata for accuracy before publishing.
