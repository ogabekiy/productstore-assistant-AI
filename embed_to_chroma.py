import argparse
import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2


DATA_FILES = (
    ("data/dokon-info.jsonl", "store_info"),
    ("data/product-chunks-pandas.jsonl", "product"),
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} JSON xato: {exc}") from exc
    return rows


def clean_metadata(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False)


def build_records(data_dir: Path) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for relative_path, doc_type in DATA_FILES:
        path = data_dir / Path(relative_path).name
        rows = read_jsonl(path)

        for row in rows:
            content = (row.get("content") or row.get("text") or "").strip()
            row_id = str(row.get("id") or "").strip()
            if not row_id:
                raise ValueError(f"{path} ichida id yo'q row bor: {row}")
            if not content:
                raise ValueError(f"{path} ichida content/text bo'sh: {row_id}")

            ids.append(f"{doc_type}:{row_id}")
            documents.append(content)
            metadatas.append(
                {
                    "doc_type": doc_type,
                    **{
                        key: clean_metadata(value)
                        for key, value in row.items()
                        if key not in {"content", "text"}
                    },
                }
            )

    if len(ids) != len(set(ids)):
        raise ValueError("Takrorlangan document id topildi.")

    return ids, documents, metadatas


def batched(items: list[Any], batch_size: int) -> list[list[Any]]:
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ProductStore JSONL chunklarini ChromaDB ga embedding qilib yuklash."
    )
    parser.add_argument("--data-dir", default="data", help="JSONL fayllar joylashgan papka.")
    parser.add_argument("--db-dir", default="chroma_db", help="ChromaDB persistent papkasi.")
    parser.add_argument("--collection", default="productstore_rag", help="Chroma collection nomi.")
    parser.add_argument("--batch-size", type=int, default=64, help="Yuklash batch hajmi.")
    parser.add_argument("--reset", action="store_true", help="Collectionni qayta yaratish.")
    args = parser.parse_args()

    ids, documents, metadatas = build_records(Path(args.data_dir))

    ONNXMiniLM_L6_V2.DOWNLOAD_PATH = (
        Path(".cache") / "chroma" / "onnx_models" / ONNXMiniLM_L6_V2.MODEL_NAME
    )
    embedding_function = DefaultEmbeddingFunction()
    client = chromadb.PersistentClient(path=args.db_dir)

    if args.reset:
        try:
            client.delete_collection(args.collection)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=args.collection,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )

    for ids_batch, docs_batch, metas_batch in zip(
        batched(ids, args.batch_size),
        batched(documents, args.batch_size),
        batched(metadatas, args.batch_size),
    ):
        collection.upsert(ids=ids_batch, documents=docs_batch, metadatas=metas_batch)

    print(f"Yuklandi: {collection.count()} ta document")
    print(f"DB papka: {Path(args.db_dir).resolve()}")
    print(f"Collection: {args.collection}")

    sample = collection.query(
        query_texts=["iPhone narxi qancha va kafolati bormi?"],
        n_results=3,
    )
    print("\nTest query natijalari:")
    for index, document_id in enumerate(sample["ids"][0], start=1):
        metadata = sample["metadatas"][0][index - 1]
        title = metadata.get("name") or metadata.get("title") or document_id
        print(f"{index}. {title} ({document_id})")


if __name__ == "__main__":
    main()
