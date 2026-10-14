FROM python:3.12-slim AS base
WORKDIR /app
COPY from-plant-to-watershed/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY from-plant-to-watershed/backend ./from-plant-to-watershed/backend
COPY from-plant-to-watershed/research_domain ./from-plant-to-watershed/research_domain
WORKDIR /app/from-plant-to-watershed/backend
ENV PYTHONPATH=/app/from-plant-to-watershed/backend

FROM base AS development
COPY from-plant-to-watershed/backend/requirements-dev.txt ./requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS swat-runtime-bundle
COPY deploy/swat-runtime.tar.gz /tmp/swat-runtime.tar.gz
COPY deploy/swat-runtime.sha256 /tmp/swat-runtime.sha256
RUN python deployment/swat_runtime.py install \
    --archive /tmp/swat-runtime.tar.gz \
    --sha256 "$(cat /tmp/swat-runtime.sha256)" \
    && rm -f /tmp/swat-runtime.tar.gz /tmp/swat-runtime.sha256

FROM base AS runtime
COPY --from=swat-runtime-bundle /app/from-plant-to-watershed/backend/data/swat-runtime ./data/swat-runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgfortran5 && rm -rf /var/lib/apt/lists/*
EXPOSE 8000
CMD ["sh", "deployment/start.sh"]
