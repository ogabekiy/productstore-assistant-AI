import os

import anthropic
from dotenv import load_dotenv


load_dotenv()

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "claude-haiku-5-5")
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "1500"))

client = anthropic.Anthropic()


def extract_text(response: anthropic.types.Message) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


def ask(
    prompt: str,
    system: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    model: str = DEFAULT_MODEL,
) -> str:
    """Claude'ga so'rov yuboradi va matn javobini qaytaradi."""
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    if system:
        kwargs["system"] = system

    try:
        response = client.messages.create(**kwargs)
    except anthropic.RateLimitError:
        return "Xato: so'rovlar limiti oshib ketdi, birozdan keyin urinib ko'ring."
    except anthropic.AuthenticationError:
        return "Xato: API kalit noto'g'ri yoki .env faylida topilmadi."
    except anthropic.APIError as e:
        return f"API xatosi: {e}"

    usage = response.usage
    print(f"[Token: {usage.input_tokens} kirish / {usage.output_tokens} chiqish]")
    return extract_text(response)


if __name__ == "__main__":
    javob = ask(
        prompt="Salom",
        system="O'zbek tilida, qisqa va xushmuomala javob bering.",
    )
    print(javob)
