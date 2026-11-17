import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("arcos.model")

MODEL_NAME = os.getenv("ROOT_AGENT_MODEL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if "gemini" in MODEL_NAME.lower():
    from langchain_google_genai import ChatGoogleGenerativeAI

    if GEMINI_API_KEY:
        logger.info(f"Modelo:{MODEL_NAME} (Gemini API)")
        model = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            api_key=GEMINI_API_KEY,
            temperature=1.0,
        )
    else:
        logger.info(f"Modelo:{MODEL_NAME} (Vertex AI)")
        model = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION"),
            temperature=1.0,
        )
else:
    logger.info(f"Modelo: {MODEL_NAME} (Ollama)")
    from langchain_ollama import ChatOllama

    model = ChatOllama(
        model=MODEL_NAME,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        num_ctx=16384,
        temperature=0.6,
        reasoning=False,
    )
