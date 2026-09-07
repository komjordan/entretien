FROM python:3.12-slim-bookworm

# wkhtmltopdf n'est plus dans les dépôts Debian officiels : on installe
# le .deb publié par le projet lui-même.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fontconfig \
    libjpeg62-turbo \
    libxrender1 \
    libxext6 \
    xfonts-75dpi \
    xfonts-base \
    && curl -fsSL -o /tmp/wkhtmltox.deb \
       https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb \
    && rm /tmp/wkhtmltox.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
