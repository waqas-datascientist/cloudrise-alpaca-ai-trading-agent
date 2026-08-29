FROM python:3.12-alpine

WORKDIR /app
COPY . /app

RUN addgroup -S cloudrise \
    && adduser -S cloudrise -G cloudrise \
    && chown -R cloudrise:cloudrise /app

USER cloudrise
ENV CLOUDRISE_MODE=demo \
    CLOUDRISE_HOST=0.0.0.0 \
    PORT=8787 \
    PYTHONUNBUFFERED=1

EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health', timeout=3)"

CMD ["python", "-m", "cloudrise", "serve"]
