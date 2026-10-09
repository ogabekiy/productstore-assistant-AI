from pathlib import Path
from typing import Any
from datetime import datetime
from zoneinfo import ZoneInfo

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

from chat_to_claude import ask


DB_DIR = "chroma_db"
COLLECTION_NAME = "productstore_rag"
TOP_K = 5
TIMEZONE = "Asia/Tashkent"
OPEN_HOUR = 10
OPEN_MINUTE = 0
CLOSE_HOUR = 21
CLOSE_MINUTE = 0


SYSTEM_PROMPT = """
Siz ProductStore do'konining AI yordamchisisiz.
Faqat berilgan CONTEXT asosida javob bering.
Agar context ichida aniq javob topilmasa, bu malumot topilmagani muloyimlik bilan tushuntiring.
Narx, kafolat, yetkazib berish va mahsulot xususiyatlarida taxmin qilmang.
O'zbek tilida, qisqa, aniq va xushmuomala javob bering.
Muomala uslubi do'kondagi tajribali sotuvchidek bo'lsin: muloyim, foydali va ortiqcha gaplarsiz.
Keraksiz texnik tafsilotlar, source nomlari yoki context haqida izoh yubormang.
Mijozning ehtiyoji noaniq bo'lsa, javob oxirida faqat 1 ta qisqa aniqlashtiruvchi savol bering.
Agar bir nechta mos variant bo'lsa, eng mos 1-2 tasini tavsiya qiling va sababini qisqa ayting.
Narx e'tirozida bahslashmang; contextdagi faktlar bilan qiymat, kafolat va qulaylikni muloyim tushuntiring.
Yolg'on chegirma, yolg'on shoshilinchlik, yolg'on stock yoki mavjud bo'lmagan imkoniyatlarni aytmang.
Mijozga bosim qilmang; sotishdan ko'ra to'g'ri tanlashga yordam berishni ustun qo'ying.
""".strip()


TIME_KEYWORDS = (
    "soat",
    "vaqt",
    "sana",
    "bugun",
    "hozir",
    "kun",
    "oy",
    "yil",
    "date",
    "time",
)

OPEN_STATUS_KEYWORDS = (
    "ochiq",
    "yopiq",
    "ishlayaptimi",
    "ishlaydimi",
    "borsam",
    "boraymi",
    "qabul",
)

STORE_INFO_HINTS = {
    "store_info:aloqa": (
        "manzil",
        "adres",
        "address",
        "lokatsiya",
        "location",
        "qayerda",
        "qaerda",
        "xarita",
        "kontakt",
        "aloqa",
        "telefon",
    ),
    "store_info:ish-vaqti": (
        "ish vaqti",
        "ishlayaptimi",
        "ishlaydimi",
        "ochiq",
        "yopiq",
        "soat nechagacha",
        "qachon ishlaydi",
        "borsam",
        "boraymi",
    ),
}


def get_collection() -> chromadb.Collection:
    ONNXMiniLM_L6_V2.DOWNLOAD_PATH = (
        Path(".cache") / "chroma" / "onnx_models" / ONNXMiniLM_L6_V2.MODEL_NAME
    )
    embedding_function = DefaultEmbeddingFunction()
    client = chromadb.PersistentClient(path=DB_DIR)
    return client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
    )


def get_hint_ids(question: str) -> list[str]:
    normalized = question.lower()
    return [
        document_id
        for document_id, keywords in STORE_INFO_HINTS.items()
        if any(keyword in normalized for keyword in keywords)
    ]


def get_contexts_by_ids(collection: chromadb.Collection, ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []

    result = collection.get(
        ids=ids,
        include=["documents", "metadatas"],
    )
    contexts: list[dict[str, Any]] = []
    for document, metadata in zip(result["documents"], result["metadatas"]):
        contexts.append(
            {
                "document": document,
                "metadata": metadata,
                "distance": 0,
            }
        )
    return contexts


def search_context(question: str, top_k: int = TOP_K) -> list[dict[str, Any]]:
    collection = get_collection()
    contexts = get_contexts_by_ids(collection, get_hint_ids(question))

    result = collection.query(
        query_texts=[question],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    seen_ids = {item["metadata"].get("id") for item in contexts}
    for document, metadata, distance in zip(
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        if metadata.get("id") in seen_ids:
            continue
        contexts.append(
            {
                "document": document,
                "metadata": metadata,
                "distance": distance,
            }
        )
    return contexts


def format_context(contexts: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for index, item in enumerate(contexts, start=1):
        metadata = item["metadata"]
        title = metadata.get("name") or metadata.get("title") or metadata.get("id")
        source = metadata.get("source_url") or metadata.get("source") or "local data"
        parts.append(
            f"[{index}] {title}\n"
            f"Manba: {source}\n"
            f"Matn:\n{item['document']}"
        )
    return "\n\n---\n\n".join(parts)


def build_prompt(question: str, contexts: list[dict[str, Any]]) -> str:
    context_text = format_context(contexts)
    return f"""
CONTEXT:
{context_text}

SAVOL:
{question}

JAVOB:
""".strip()


def is_time_question(question: str) -> bool:
    normalized = question.lower()
    has_time_word = any(keyword in normalized for keyword in TIME_KEYWORDS)
    has_store_status_word = any(keyword in normalized for keyword in OPEN_STATUS_KEYWORDS)
    return has_time_word and not has_store_status_word


def answer_time_question() -> str:
    now = datetime.now(ZoneInfo(TIMEZONE))
    return now.strftime("Hozir Toshkent vaqti bilan %H:%M, sana %d.%m.%Y.")


def is_open_status_question(question: str) -> bool:
    normalized = question.lower()
    has_store_status_word = any(keyword in normalized for keyword in OPEN_STATUS_KEYWORDS)
    has_store_word = any(word in normalized for word in ("do'kon", "dokon", "product", "pro duct"))
    return has_store_status_word and (has_store_word or "borsam" in normalized or "boraymi" in normalized)


def answer_open_status_question() -> str:
    now = datetime.now(ZoneInfo(TIMEZONE))
    open_time = now.replace(hour=OPEN_HOUR, minute=OPEN_MINUTE, second=0, microsecond=0)
    close_time = now.replace(hour=CLOSE_HOUR, minute=CLOSE_MINUTE, second=0, microsecond=0)
    is_open = open_time <= now <= close_time

    if is_open:
        return (
            f"Ha, hozir do'kon ochiq. Ish vaqti har kuni 10:00–21:00, "
            f"hozir Toshkent vaqti bilan {now:%H:%M}. Bemalol borishingiz mumkin."
        )

    return (
        f"Hozir do'kon yopiq. Ish vaqti har kuni 10:00–21:00, "
        f"hozir Toshkent vaqti bilan {now:%H:%M}."
    )


def rag_answer(question: str, top_k: int = TOP_K) -> str:
    if is_open_status_question(question):
        return answer_open_status_question()

    if is_time_question(question):
        return answer_time_question()

    contexts = search_context(question, top_k=top_k)
    prompt = build_prompt(question, contexts)
    return ask(prompt=prompt, system=SYSTEM_PROMPT, max_tokens=900)


def main() -> None:
    print("ProductStore RAG Assistant. Chiqish uchun 'exit' yozing.")
    while True:
        question = input("\nSavol: ").strip()
        if question.lower() in {"exit", "quit", "q"}:
            break
        if not question:
            continue

        answer = rag_answer(question)
        print(f"\nJavob: {answer}")


if __name__ == "__main__":
    main()
