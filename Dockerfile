FROM python:3.12-slim

# Stockfish from Debian repos lands at /usr/games/stockfish
RUN apt-get update \
    && apt-get install -y --no-install-recommends stockfish \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    STOCKFISH_PATH=/usr/games/stockfish \
    DATA_DIR=/data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Profiles + SQLite live here; mount a persistent volume at /data so they
# survive redeploys.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
