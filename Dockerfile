FROM python:3.12-slim

# Dependências de sistema do WeasyPrint (Pango, Cairo, fontes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8 \
    libgdk-pixbuf-2.0-0 libcairo2 fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY orcamento_core.py app.py eventopia_logo.png ./

EXPOSE 8000
ENV PORT=8000
# 2 workers chega para este volume; timeout maior por causa do render
CMD ["gunicorn", "-b", "0.0.0.0:8000", "-w", "2", "--timeout", "60", "app:app"]
