FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy only the dependency files to leverage Docker layer caching
COPY pyproject.toml poetry.lock* ./

# Install project dependencies
# --no-root: Do not install the project itself, as we will mount the source code
# --no-dev: Do not install development dependencies
RUN poetry install --no-root --no-dev

# Copy the rest of the application code
COPY ./backend/src ./src

# Command to run the application
CMD ["poetry", "run", "python", "-m", "src"]
