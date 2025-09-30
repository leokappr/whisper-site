import os
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from openai import OpenAI
import streamlit.components.v1 as components

# Exports
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import cm

# ---------- Config ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
st.set_page_config(page_title="Whisper Transcripteur", layout="wide")

APP_TITLE = "🎧 Whisper Transcripteur"
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)
HISTO_PATH = DATA_DIR / "historique.json"

# ---------- Fonctions utiles ----------
def load_history():
    if HISTO_PATH.exists():
        try:
            return json.loads(HISTO_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_history(histo):
    HISTO_PATH.write_text(json.dumps(histo, ensure_ascii=False, indent=2), encoding="utf-8")

def normalize_paragraphs(text: str):
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if "\n\n" in t:
        parts = [p.strip() for p in t.split("\n\n") if p.strip()]
    else:
        parts = [p.strip() for p in t.split("\n") if p.strip()]
    return parts

def export_docx(content: str, out_path: Path):
    doc = Document()
    doc.add_heading("Transcription", level=1)
    for p in normalize_paragraphs(content):
        doc.add_paragraph(p)
    doc.save(out_path)

def export_pdf(content: str, out_path: Path):
    doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    style_h1 = styles["Heading1"]
    style_p = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=18,
        spaceAfter=10
    )

    story = [Paragraph("Transcription", style_h1), Spacer(1, 12)]
    for p in normalize_paragraphs(content):
        safe = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(safe, style_p))
        story.append(Spacer(1, 6))
    doc.build(story)

# ---------- Interface ----------
st.sidebar.header("Menu")
page = st.sidebar.radio(" ", ["🎙️ Transcrire", "📚 Historique", "⚙️ Paramètres"], label_visibility="collapsed")

st.title(APP_TITLE)

if page == "🎙️ Transcrire":
    st.subheader("Importer un fichier audio")
    file = st.file_uploader("Formats acceptés : MP3, M4A, WAV", type=["mp3", "m4a", "wav"])

    # Étape 1 : faire la transcription une seule fois
    if file and "transcript" not in st.session_state:
        with st.spinner("🧠 Transcription en cours..."):
            tmp_path = Path(file.name)
            with open(tmp_path, "wb") as f:
                f.write(file.getbuffer())

            with open(tmp_path, "rb") as af:
                transcript_text = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=af,
                    response_format="text"
                )

        st.session_state.transcript = transcript_text
        st.session_state.filename = file.name
        st.success("✅ Transcription terminée !")

        # Sauvegarde historique
        histo = load_history()
        histo.append({
            "name": file.name,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "text": transcript_text[:5000]
        })
        save_history(histo)

    # Étape 2 : zone de texte et actions (pas de retranscription)
    if "transcript" in st.session_state:
        edited = st.text_area(
            "📝 Transcription (modifiable avant export)",
            st.session_state.transcript,
            height=420
        )

        st.session_state.transcript = edited

        col1, col2, col3 = st.columns([1, 1, 1])

        # Copier
        with col1:
            if st.button("📋 Copier"):
                components.html(
                    f'<script>navigator.clipboard.writeText({json.dumps(edited)});</script>',
                    height=0,
                )
                st.toast("Texte copié dans le presse-papiers ✅")

        out_dir = Path.cwd()
        docx_path = out_dir / "transcription.docx"
        pdf_path  = out_dir / "transcription.pdf"

        # DOCX
        with col2:
            if st.button("📄 Générer DOCX"):
                export_docx(edited, docx_path)
                st.download_button("⬇️ Télécharger DOCX", docx_path.read_bytes(), file_name="transcription.docx")

        # PDF
        with col3:
            if st.button("🧾 Générer PDF"):
                export_pdf(edited, pdf_path)
                st.download_button("⬇️ Télécharger PDF", pdf_path.read_bytes(), file_name="transcription.pdf")

elif page == "📚 Historique":
    st.subheader("Historique des transcriptions")
    histo = load_history()
    if not histo:
        st.info("Aucune transcription enregistrée pour le moment.")
    else:
        for item in reversed(histo[-50:]):
            with st.expander(f"📝 {item['name']} — {item['date']}"):
                st.write(item.get("text", ""))

elif page == "⚙️ Paramètres":
    st.subheader("Paramètres")
    st.markdown("- Modèle : **whisper-1**")
    st.markdown("- Langue : **auto**")
    st.markdown("- Exports : **DOCX / PDF** formatés")

