# Image légère Python + ffmpeg inclus pour Whisper
FROM python:3.11-slim

# Empêche les fichiers .pyc et affiche les logs directement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dossier de travail
WORKDIR /app

# Installe ffmpeg pour traiter les fichiers audio
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copie des dépendances et installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY whisper_site.py .

# Port et commande de démarrage
ENV PORT=10000
CMD ["sh", "-c", "streamlit run whisper_site.py --server.port=$PORT --server.address=0.0.0.0"]

