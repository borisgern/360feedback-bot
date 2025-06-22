.PHONY: help dev down

help:
	@echo "Available commands:"
	@echo "  dev       - Start the development environment using Docker Compose."
	@echo "  down      - Stop and remove the development environment."

dev:
	docker-compose -f infra/docker-compose.yml up --build

down:
	docker-compose -f infra/docker-compose.yml down
