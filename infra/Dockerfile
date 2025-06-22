# ---- 1. Base image ----------------------------------------------------------
FROM python:3.13-slim

# ---- 2. Set workdir ---------------------------------------------------------
WORKDIR /app

# ---- 3. Install Poetry (latest 2.x) -----------------------------------------
RUN pip install --no-cache-dir poetry

# ---- 4. Copy only dependency manifests first (layer caching) ---------------
COPY pyproject.toml poetry.lock* ./

# ---- 5. Install ONLY production deps ----------------------------------------
RUN poetry install --only main --no-root --no-interaction

# ---- 6. Copy the rest of the source code ------------------------------------
COPY backend ./backend

# ---- 7. Default command ------------------------------------------------------
CMD ["poetry", "run", "python", "-m", "backend.src"]
