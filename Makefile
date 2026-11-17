.PHONY: help create-env delete-env run web chat-history chat-history-pretty

PYTHON_VERSION := 3.13.12

help:
	@echo "ARCOS Agent UERJ Makefile Commands:"
	@echo ""
	@echo "Environment Management:"
	@echo "  create-env              Create virtual environment and install dependencies (uv sync)"
	@echo "  delete-env              Delete Python virtual environment"
	@echo ""
	@echo "Running:"
	@echo "  run                     Run the agent in the terminal (python3 -m agents.main)"
	@echo "  web                     Run Streamlit web interface (ui/app_streamlit.py)"
	@echo ""
	@echo "Database:"
	@echo "  chat-history            View raw chat history (JSON)"
	@echo "  chat-history-pretty     View formatted chat history (readable)"
	@echo ""

create-env:
	@echo "Creating virtual environment with Python ${PYTHON_VERSION}..."
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "Error: uv is not installed. Please install uv first."; \
		exit 1; \
	fi
	@echo "Installing dependencies from pyproject.toml / uv.lock..."
	@uv sync --python ${PYTHON_VERSION}
	@echo "Virtual environment created and dependencies installed successfully!"

delete-env:
	@echo "Deleting virtual environment..."
	@if [ -d ".venv" ]; then \
		rm -rf .venv; \
		echo "Virtual environment deleted successfully!"; \
	else \
		echo "Virtual environment not found."; \
	fi

run:
	@python3 -m agents.main

web:
	@streamlit run ui/app_streamlit.py

chat-history:
	@sqlite3 ./db/sessions.db ".mode column" ".headers on" "SELECT * FROM message_store;"

f-chat-history:
	@python3 db/chat_history_pretty.py
