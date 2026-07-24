.PHONY: help create-env delete-env run web chat-history chat-history-pretty

PYTHON_VERSION := 3.13.12

help:
	@echo "ARCOS Agent UERJ Makefile Commands:"
	@echo ""
	@echo "Environment Management:"
	@echo "  create-env              Create Python virtual environment"
	@echo "  delete-env              Delete Python virtual environment"
	@echo ""
	@echo "Running:"
	@echo "  run                     Run the agent (cmd)"
	@echo "  web                     Run Streamlit web interface"
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

run:
	@echo "Waking up ARCOS Agent..."
	@python3 agent.py

web:
	@echo "Starting Streamlit server..."
	@echo "Streamlit will display its local URL below:"
	@streamlit run app_streamlit.py
	
