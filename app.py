import io
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
import streamlit as st

APP_TITLE = "AI Music Analyzer & YouTube SEO Studio"
SUPPORTED_AUDIO = ["mp3", "wav", "m4a", "flac", "ogg", "mp4", "webm"]

st.set_page_config(page_title=APP_TITLE, page_icon="🎵", layout="wide")

def extract_video_id(url: str):
    try:
        parsed = urlparse(url.strip())
        host = (parsed.netloc or "").lower().replace("www.", "")
        if host in {"youtu.be", "m.youtube.com", "youtube.com", "music.youtube.com"}:
            if host == "youtu.be":
                candidate = parsed.path.strip("/").split("/")[0]
            else:
                if parsed.path == "/watch":
                    candidate = parse_qs(parsed.query).get("v", [""])[0]
                else:
                    match = re.match(r"^/(?:shorts|embed|live)/([^/?]+)", parsed.path)
                    candidate = match.group(1) if match else ""
            return candidate if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate or "") else None
    except Exception:
        return None
    return None

def fetch_youtube_metadata(url: str):
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("URL YouTube tidak dikenali. Gunakan link video, Shorts, atau youtu.be yang valid.")
    endpoint = "https://www.youtube.com/oembed"
    response = requests.get(endpoint, params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"}, timeout=15)
    if response.status_code != 200:
        raise ValueError("Metadata tidak bisa diambil. Video mungkin privat, dibatasi, atau link tidak valid.")
    data = response.json()
    return {
        "video_id": video_id,
        "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
        "title": data.get("title", ""),
        "channel": data.get("author_name", ""),
        "thumbnail": data.get("thumbnail_url", ""),
        "embed_url": f"https://www.youtube-nocookie.com/embed/{video_id}",
    }

def analyze_audio_file(uploaded_file):
    import numpy as np
    import librosa

    suffix = Path(uploaded_file.name).suffix.lower().lstrip(".")
    if suffix not in SUPPORTED_AUDIO:
        raise ValueError(f"Format tidak didukung. Gunakan: {', '.join(SUPPORTED_AUDIO)}")
    raw = uploaded_file.getvalue()
    with tempfile.NamedTemporaryFile(delete=False, suffix="." + suffix) as temp:
        temp.write(raw)
        temp_path = temp.name
    try:
        y, sr = librosa.load(temp_path, sr=22050, mono=True, duration=600)
        if len(y) < sr:
            raise ValueError("Audio terlalu pendek untuk dianalisis (minimal sekitar 1 detik).")
        duration = len(y) / sr
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo_value = float(np.asarray(tempo).reshape(-1)[0])
        rms = float(np.mean(librosa.feature.rms(y=y)))
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
        contrast = float(np.mean(librosa.feature.spectral_contrast(y=y, sr=sr)))
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        key_names = ["C", "C♯/D♭", "D", "D♯/E♭", "E", "F", "F♯/G♭", "G", "G♯/A♭", "A", "A♯/B♭", "B"]
        likely_key = key_names[int(np.argmax(chroma_mean))]
        mood = "energetic / upbeat" if tempo_value >= 115 and rms > 0.08 else ("calm / mellow" if tempo_value < 90 else "moderate / balanced")
        brightness = "bright" if centroid > 2500 else ("warm / dark" if centroid < 1400 else "balanced")
        return {
            "duration_seconds": round(duration, 1),
            "sample_rate": sr,
            "tempo_bpm_estimate": round(tempo_value, 1),
            "estimated_key": likely_key,
            "mood_heuristic": mood,
            "timbre_brightness_heuristic": brightness,
            "rms_energy": round(rms, 4),
            "spectral_centroid_hz": round(centroid, 1),
            "zero_crossing_rate": round(zcr, 4),
            "spectral_contrast": round(contrast, 3),
            "note": "Tempo, key, mood, and timbre are estimates from simple signal features, not ground-truth labels.",
        }
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

def transcribe_audio(uploaded_file, language_choice):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Paket faster-whisper belum terpasang. Install requirements.txt lalu restart aplikasi.") from exc

    suffix = Path(uploaded_file.name).suffix.lower() or ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(uploaded_file.getvalue())
        temp_path = temp.name
    try:
        # CPU/int8 keeps this usable on modest hardware; first run downloads model weights.
        model = WhisperModel("small", device="cpu", compute_type="int8")
        language = None if language_choice == "Auto detect" else ("en" if language_choice == "English" else "id")
        segments, info = model.transcribe(temp_path, language=language, vad_filter=True)
        rows = []
        for seg in segments:
            rows.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
        transcript = "\n".join(row["text"] for row in rows)
        srt_parts = []
        for index, row in enumerate(rows, start=1):
            def stamp(seconds):
                millis = int(round(seconds * 1000))
                hours, rem = divmod(millis, 3600000)
                minutes, rem = divmod(rem, 60000)
                secs, ms = divmod(rem, 1000)
                return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"
            srt_parts.append(f"{index}\n{stamp(row['start'])} --> {stamp(row['end'])}\n{row['text']}\n")
        return {
            "language": getattr(info, "language", "unknown"),
            "language_probability": round(float(getattr(info, "language_probability", 0)), 3),
            "transcript": transcript,
            "srt": "\n".join(srt_parts),
            "segments": rows,
        }
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

def generate_seo(title, channel, genre, mood, language, keywords, transcript):
    clean_title = title.strip() or "Original Music"
    channel = channel.strip() or "Artist / Channel"
    keywords = [x.strip() for x in keywords.split(",") if x.strip()]
    keyword_text = ", ".join(keywords[:12])
    genre = genre.strip() or "music"
    mood = mood.strip() or "emotional"
    excerpt = (transcript or "").strip()
    excerpt = excerpt[:700]
    en_title = f"{clean_title} | {genre.title()} Music • {mood.title()} Vibes"
    id_title = f"{clean_title} | Musik {genre.title()} • Suasana {mood.title()}"
    en_desc = (
        f"Listen to {clean_title} by {channel}. This track brings {mood.lower()} vibes with a {genre.lower()} sound.\n\n"
        f"🎧 Enjoy the music? Like, comment, and subscribe for more music and new releases.\n"
        f"🔎 Topics: {keyword_text or genre + ', ' + mood + ', new music'}\n\n"
        "Please add accurate artist, producer, and rights credits before publishing. Do not claim ownership of music you do not own."
    )
    id_desc = (
        f"Dengarkan {clean_title} dari {channel}. Lagu ini menghadirkan nuansa {mood.lower()} dengan karakter musik {genre.lower()}.\n\n"
        f"🎧 Suka musik ini? Jangan lupa like, tulis komentar, dan subscribe untuk rilisan berikutnya.\n"
        f"🔎 Topik: {keyword_text or genre + ', ' + mood + ', musik terbaru'}\n\n"
        "Pastikan menambahkan kredit artis, produser, dan informasi hak cipta yang benar sebelum publikasi. Jangan mengklaim kepemilikan musik yang bukan milik Anda."
    )
    tags = list(dict.fromkeys([clean_title, channel, genre, mood, "music", "new music", "official audio", "musik", "lagu", *keywords]))
    hashtags = " ".join("#" + re.sub(r"[^A-Za-z0-9_]", "", x.replace(" ", "")) for x in [genre, mood, "Music", "Musik"] if x)
    thumbnail_en = f"High-contrast YouTube music thumbnail for {clean_title}, {genre} genre, {mood} atmosphere, cinematic lighting, clear focal subject, space for 2-4 word title, no fake awards or misleading claims, 16:9 composition."
    thumbnail_id = f"Thumbnail YouTube musik {clean_title}, genre {genre}, suasana {mood}, pencahayaan sinematik, subjek utama jelas, sisakan ruang untuk teks 2-4 kata, tanpa klaim menyesatkan, komposisi 16:9."
    return {
        "English": {"title": en_title, "description": en_desc, "tags": tags, "hashtags": hashtags, "thumbnail_text": "FEEL THE MUSIC", "thumbnail_prompt": thumbnail_en},
        "Bahasa Indonesia": {"title": id_title, "description": id_desc, "tags": tags, "hashtags": hashtags, "thumbnail_text": "RASAKAN MUSIKNYA", "thumbnail_prompt": thumbnail_id},
    }

st.title("🎵 AI Music Analyzer & YouTube SEO Studio")
st.caption("Analyze authorized audio, transcribe vocals, inspect basic audio features, and prepare bilingual YouTube metadata.")

with st.sidebar:
    st.header("About")
    st.write("Open-source starter project. Processing is performed by this app instance.")
    st.warning("Jangan unggah atau transkripsikan audio yang tidak Anda miliki atau tidak berizin untuk digunakan.")
    st.markdown("[Project README](https://github.com/)")

st.subheader("1. YouTube link & metadata")
youtube_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
metadata = None
if st.button("Ambil metadata video", type="primary"):
    if not youtube_url.strip():
        st.error("Masukkan link YouTube terlebih dahulu.")
    else:
        try:
            with st.spinner("Mengambil metadata publik..."):
                metadata = fetch_youtube_metadata(youtube_url)
                st.session_state["yt_metadata"] = metadata
        except Exception as exc:
            st.error(str(exc))
if "yt_metadata" in st.session_state:
    metadata = st.session_state["yt_metadata"]
    col1, col2 = st.columns([1, 2])
    with col1:
        if metadata.get("thumbnail"):
            st.image(metadata["thumbnail"], use_container_width=True)
        st.link_button("Buka video YouTube", metadata["canonical_url"])
    with col2:
        st.markdown(f"**Judul:** {metadata['title']}")
        st.markdown(f"**Channel:** {metadata['channel']}")
        st.components.v1.iframe(metadata["embed_url"], height=220, scrolling=False)
    default_title = metadata["title"]
    default_channel = metadata["channel"]
else:
    default_title = ""
    default_channel = ""

st.info("Batasan penting: link YouTube dipakai untuk metadata publik dan embed saja. Aplikasi ini tidak mengunduh atau meripping audio dari YouTube. Untuk analisis audio/lirik, unggah file audio yang Anda miliki atau punya izin untuk memproses.")

st.subheader("2. Upload audio yang Anda berhak gunakan")
audio_file = st.file_uploader("Pilih file audio/video", type=SUPPORTED_AUDIO)
analysis = None
transcription = None
if audio_file:
    st.audio(audio_file)
    left, right = st.columns(2)
    with left:
        if st.button("Analisis karakter musik"):
            try:
                with st.spinner("Menganalisis audio (maksimal 10 menit pada konfigurasi awal)..."):
                    analysis = analyze_audio_file(audio_file)
                    st.session_state["analysis"] = analysis
            except Exception as exc:
                st.error(f"Gagal menganalisis audio: {exc}")
    with right:
        language_choice = st.selectbox("Bahasa transkripsi", ["Auto detect", "English", "Bahasa Indonesia"])
        if st.button("Transkripsikan vokal / lirik"):
            try:
                with st.spinner("Memuat model Whisper dan mentranskripsikan..."):
                    transcription = transcribe_audio(audio_file, language_choice)
                    st.session_state["transcription"] = transcription
            except Exception as exc:
                st.error(f"Gagal transkripsi: {exc}")

if "analysis" in st.session_state:
    analysis = st.session_state["analysis"]
    st.subheader("Hasil analisis audio")
    a, b, c, d = st.columns(4)
    a.metric("Durasi", f"{analysis['duration_seconds']} detik")
    b.metric("Tempo perkiraan", f"{analysis['tempo_bpm_estimate']} BPM")
    c.metric("Nada dasar perkiraan", analysis["estimated_key"])
    d.metric("Mood heuristik", analysis["mood_heuristic"])
    st.json(analysis)

if "transcription" in st.session_state:
    transcription = st.session_state["transcription"]
    st.subheader("Hasil transkripsi")
    st.write(f"Bahasa terdeteksi: **{transcription['language']}** (probabilitas {transcription['language_probability']})")
    st.text_area("Transkrip", transcription["transcript"], height=220)
    st.download_button("Unduh lirik TXT", transcription["transcript"], file_name="lyrics.txt", mime="text/plain")
    st.download_button("Unduh subtitle SRT", transcription["srt"], file_name="lyrics.srt", mime="application/x-subrip")

st.subheader("3. Generate YouTube SEO (English + Bahasa Indonesia)")
with st.form("seo_form"):
    seo_title = st.text_input("Judul lagu / video", value=default_title)
    seo_channel = st.text_input("Artis / channel", value=default_channel)
    genre = st.text_input("Genre / style musik", placeholder="lofi, pop rock, cinematic ambient...")
    mood = st.text_input("Mood / suasana", placeholder="calm, uplifting, nostalgic...")
    keyword_input = st.text_input("Kata kunci (pisahkan dengan koma)", placeholder="relaxing music, original song, musik santai")
    transcript_for_seo = st.text_area("Lirik atau konteks lagu (opsional)", value=st.session_state.get("transcription", {}).get("transcript", ""), height=100)
    submitted = st.form_submit_button("Buat paket SEO bilingual", type="primary")
if submitted:
    seo_result = generate_seo(seo_title, seo_channel, genre, mood, "both", keyword_input, transcript_for_seo)
    st.session_state["seo_result"] = seo_result

if "seo_result" in st.session_state:
    seo_result = st.session_state["seo_result"]
    tabs = st.tabs(["English", "Bahasa Indonesia", "JSON export"])
    for tab, lang in zip(tabs[:2], ["English", "Bahasa Indonesia"]):
        with tab:
            data = seo_result[lang]
            st.text_input(f"Title — {lang}", value=data["title"], key=f"title_{lang}")
            st.text_area(f"Description — {lang}", value=data["description"], height=220, key=f"desc_{lang}")
            st.text_area(f"Tags — {lang}", value=", ".join(data["tags"]), height=90, key=f"tags_{lang}")
            st.text_input(f"Hashtags — {lang}", value=data["hashtags"], key=f"hash_{lang}")
            st.text_input(f"Thumbnail text — {lang}", value=data["thumbnail_text"], key=f"thumbtxt_{lang}")
            st.text_area(f"Thumbnail prompt — {lang}", value=data["thumbnail_prompt"], height=100, key=f"thumbprompt_{lang}")
    with tabs[2]:
        export = {
            "youtube": st.session_state.get("yt_metadata"),
            "audio_analysis": st.session_state.get("analysis"),
            "transcription": st.session_state.get("transcription"),
            "seo": seo_result,
        }
        st.json(export)
        st.download_button("Unduh seluruh paket JSON", json.dumps(export, ensure_ascii=False, indent=2), file_name="music_youtube_seo_package.json", mime="application/json")

st.divider()
st.caption("SEO helper generates drafts, not ranking guarantees. Review accuracy, rights, credits, and YouTube policies before publishing.")
