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

# ---------- Config & helpers ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

APP_TITLE = "🎧 Whisper Transcripteur"
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)
HISTO_PATH = DATA_DIR / "historique.json"

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
    # Si l'utilisateur a mis des lignes vides pour séparer les blocs, on les respecte
    if "\n\n" in t:
        parts = [p.strip() for p in t.split("\n\n") if p.strip()]
    else:
        # Sinon, on plie ligne par ligne (en supprimant les vides)
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
        leading=18,      # interligne
        spaceAfter=10    # espace après chaque paragraphe
    )

    story = [Paragraph("Transcription", style_h1), Spacer(1, 12)]
    for p in normalize_paragraphs(content):
        safe = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(safe, style_p))
        story.append(Spacer(1, 6))
    doc.build(story)

# ---------- UI ----------
st.set_page_config(page_title="Whisper Transcripteur", layout="wide")
st.sidebar.header("Menu")
page = st.sidebar.radio(" ", ["🎙️ Transcrire", "📚 Historique", "⚙️ Paramètres"], label_visibility="collapsed")

st.title(APP_TITLE)

if page == "🎙️ Transcrire":
    st.subheader("Importer un fichier audio")
    file = st.file_uploader("Formats acceptés : MP3, M4A, WAV (jusqu’à ~1h).", type=["mp3", "m4a", "wav"])

    if file:
        with st.spinner("🧠 Transcription en cours..."):
            tmp_path = Path(file.name)
            with open(tmp_path, "wb") as f:
                f.write(file.getbuffer())

            with open(tmp_path, "rb") as af:
                # Transcription brute (langue auto)
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=af,
                    response_format="text"
                )

        st.success("✅ Transcription terminée.")
        if "text_value" not in st.session_state:
            st.session_state.text_value = transcript

        st.write("Corrige si besoin, puis exporte en DOCX / PDF :")
        edited = st.text_area("📝 Transcription (modifiable)", st.session_state.text_value, height=420)
        st.session_state.text_value = edited  # garde la version corrigée

        # Actions : Copier / DOCX / PDF
        col1, col2, col3 = st.columns([1, 1, 1])
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

        with col2:
            if st.button("📄 Générer DOCX"):
                export_docx(edited, docx_path)
                st.download_button("⬇️ Télécharger DOCX", docx_path.read_bytes(), file_name="transcription.docx")

        with col3:
            if st.button("🧾 Générer PDF (mise en page)"):
                export_pdf(edited, pdf_path)
                st.download_button("⬇️ Télécharger PDF", pdf_path.read_bytes(), file_name="transcription.pdf")

        # Historique (sauvegarde automatique)
        histo = load_history()
        histo.append({
            "name": file.name,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "text": edited[:5000]  # on stocke un extrait raisonnable pour l'historique
        })
        save_history(histo)

elif page == "📚 Historique":
    st.subheader("Historique des transcriptions")
    histo = load_history()
    if not histo:
        st.info("Aucune transcription enregistrée pour le moment.")
    else:
        for item in reversed(histo[-50:]):  # limite affichage
            with st.expander(f"📝 {item['name']} — {item['date']}"):
                st.write(item.get("text", ""))

elif page == "⚙️ Paramètres":
    st.subheader("Paramètres")
    st.markdown("- Modèle : **whisper-1**")
    st.markdown("- Langue : **détection automatique**")
    st.markdown("- Export : **DOCX** et **PDF** avec mise en page")
    st.markdown("- Historique : stocké localement sur le serveur (effacé lors d’un redeploy)")

