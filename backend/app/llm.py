import google.generativeai as genai
from app.config import settings
import logging

genai.configure(api_key=settings.GEMINI_API_KEY)
logger = logging.getLogger(__name__)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system_prompt,
    )
    try:
        response = model.generate_content(user_prompt)
        return response.text or ""
    except Exception as e:
        logger.exception("Gemini call failed")
        return f"LLM error: {e}"
