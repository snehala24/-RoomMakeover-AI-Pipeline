import os
from dotenv import load_dotenv
import google.generativeai as genai
from langchain.prompts import PromptTemplate

load_dotenv()

# Load API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set. Please set it in your .env file.")


# Gemini setup
genai.configure(api_key=GEMINI_API_KEY)

# Allow overriding the model via env; provide sensible fallbacks (newest first)
PRIMARY_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002")
FALLBACK_GEMINI_MODELS = [
    PRIMARY_GEMINI_MODEL,
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.5-pro-002",
    "gemini-1.5-pro-latest",
    # Legacy text model (as last resort)
    "gemini-pro",
]

GENERATION_CONFIG = {
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 2048,
    # Hint the SDK we want JSON. Newer SDKs honor this via headers/params.
    "response_mime_type": "application/json",
}

# Reduce safety blocks that often yield empty responses. Adjust per policy.
SAFETY_SETTINGS = {
    # Category: threshold
    # Using BLOCK_NONE to minimize chances of empty text due to blocks
    "HATE": "BLOCK_NONE",
    "HARASSMENT": "BLOCK_NONE",
    "SEXUAL": "BLOCK_NONE",
    "DANGEROUS": "BLOCK_NONE",
}

def _try_generate_content(prompt_text: str):
    last_error = None
    def _extract_text(response_obj):
        # Prefer .text if present
        text = getattr(response_obj, "text", None)
        if text and str(text).strip():
            return str(text)
        # Try candidates -> content -> parts
        candidates = getattr(response_obj, "candidates", None) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", None) or []
            for part in parts:
                # Some SDKs store text under .text or .string_value
                if hasattr(part, "text") and str(part.text).strip():
                    return str(part.text)
                if hasattr(part, "string_value") and str(part.string_value).strip():
                    return str(part.string_value)
        # As a last resort, stringify
        try:
            return str(response_obj)
        except Exception:
            return ""

    for model_name in FALLBACK_GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name, generation_config=GENERATION_CONFIG, safety_settings=SAFETY_SETTINGS)
            # Small retries to mitigate transient empty responses
            attempts = 0
            while attempts < 2:
                attempts += 1
                response = model.generate_content(prompt_text)
                content = _extract_text(response)
                if content and str(content).strip():
                    return {"status": "success", "raw_output": content, "model_used": model_name}
            last_error = ValueError("Empty response from model after retries: " + model_name)
        except Exception as e:
            last_error = e
            # Try next fallback model
            continue
    # If static list failed, try discovered models that support generateContent
    try:
        discovered = []
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", []) or []
            if any(str(method).lower() == "generatecontent" for method in methods):
                name = getattr(m, "name", "")
                if name:
                    discovered.append(name)
        discovered_sorted = sorted(
            discovered,
            key=lambda n: (
                0 if "flash" in n.lower() else 1,
                0 if "1.5" in n else 1,
                n
            )
        )
        for model_name in discovered_sorted:
            try:
                model = genai.GenerativeModel(model_name, generation_config=GENERATION_CONFIG, safety_settings=SAFETY_SETTINGS)
                attempts = 0
                while attempts < 2:
                    attempts += 1
                    response = model.generate_content(prompt_text)
                    content = _extract_text(response)
                    if content and str(content).strip():
                        return {"status": "success", "raw_output": content, "model_used": model_name}
            except Exception as e2:
                last_error = e2
                continue
    except Exception as e_list:
        last_error = e_list
    # If all attempts failed
    message = f"Gemini invocation failed. Last error: {str(last_error)}"
    return {"status": "error", "message": message}

# Prompt template
# ✅ Updated Prompt Template
DECOR_PROMPT_TEMPLATE = """
You are an intelligent interior design assistant.

Based on the provided room description and user preferences,
create a personalized makeover plan **within ₹{budget}**.

IMPORTANT: Return ONLY a valid JSON object, no additional text or markdown formatting.

Required JSON structure:
{{
  "items": [
    {{
      "name": "Product name (e.g., white cotton bedsheet)",
      "description": "One-line purpose or aesthetic value",
      "price": 300,
      "link": "https://example.com/product"
    }}
  ],
  "total_price": 1500,
  "notes": "Suggestions or alternatives for tighter budgets"
}}

Rules:
- Ensure total_price stays within ₹{budget}
- Include 3-5 items maximum
- Use realistic prices in INR
- Provide working product links (Amazon/Flipkart/Meesho)
- Return ONLY the JSON, no explanations

Room Description: {room_description}
Preferred Style: {style}

JSON Response:
"""


def get_makeover_plan(room_description: str, budget: int, style: str = "Any") -> dict:
    prompt = PromptTemplate.from_template(DECOR_PROMPT_TEMPLATE)
    final_prompt = prompt.format(room_description=room_description, budget=budget, style=style)

    result = _try_generate_content(final_prompt)
    if result.get("status") == "success":
        raw = result.get("raw_output", "")
        model_used = result.get("model_used")
        print(f"[DEBUG] LLM Model Used: {model_used}")
        print(f"[DEBUG] LLM Raw Response: {str(raw)[:200]}...")
        # Never propagate success with empty/whitespace payload
        if not raw or not str(raw).strip():
            return {"status": "error", "message": "Empty LLM response after successful call", "model_used": model_used}
        return {"status": "success", "raw_output": raw, "model_used": model_used}
    else:
        print(f"[DEBUG] LLM Error: {result.get('message')}")
        return result
