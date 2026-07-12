.PHONY: help create-env delete-env

PYTHON_VERSION := 3.12.10

help:
	@echo "ARCOS Agent UERJ Makefile Commands:"
	@echo ""
	@echo "Environment Management:"
	@echo "  create-env          Create Python virtual environment"
	@echo "  delete-env          Delete Python virtual environment"
	@echo ""

create-env:
	@echo "Creating virtual environment with Python ${PYTHON_VERSION}..."
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "Error: uv is not installed. Please install uv first."; \
		exit 1; \
	fi
	@uv venv --python ${PYTHON_VERSION}
	@echo "Installing dependencies from requirements.txt..."
	@uv pip install --python .venv/bin/python -r requirements.txt
	@echo "Virtual environment created and dependencies installed successfully!"

delete-env:
	@echo "Deleting virtual environment..."
	@if [ -d ".venv" ]; then \
		rm -rf .venv; \
		echo "Virtual environment deleted successfully!"; \
	else \
		echo "Virtual environment not found."; \
	fi