from pathlib import Path

from agents.prompts.commons.utils import load_prompt_from_markdown

# Prompt-base (regras de domínio) herdado pelo supervisor e pelos subagentes.
# O loader lê só os .md desta pasta; os papéis ficam em subpastas/prompts de cada agente.
ROOT_PROMPT = load_prompt_from_markdown(str(Path(__file__).parent))
