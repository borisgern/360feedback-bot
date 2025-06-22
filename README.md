# 360-Feedback Bot

## Local Development

This project uses Docker and Docker Compose for a consistent development environment.

### Prerequisites

- Docker
- Docker Compose

### Setup

1.  **Create an environment file:**
    Copy the example environment file and fill in your bot token.
    ```sh
    cp .env.example .env
    ```

2.  **Run the application:**
    Use the Makefile to build and start the services.
    ```sh
    make dev
    ```

3.  **Stop the application:**
    To stop the services, run:
    ```sh
    make down
    ```
