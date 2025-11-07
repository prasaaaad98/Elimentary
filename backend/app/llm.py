import google.generativeai as genai
from app.config import settings

# Configure Gemini once
genai.configure(api_key=settings.GEMINI_API_KEY)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Calls Gemini with a system instruction + user prompt and returns the text answer.
    """
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system_prompt,
    )
    response = model.generate_content(user_prompt)
    # response.text holds the combined text output
    return response.text or ""
