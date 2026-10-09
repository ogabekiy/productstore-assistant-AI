import json
import re
from html import unescape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urljoin
from urllib.request import Request, urlopen

from main import rag_answer, search_context


HOST = "127.0.0.1"
PORT = 3000
STATIC_DIR = Path(__file__).parent / "static"
PRODUCT_IMAGE_CACHE: dict[str, list[str]] = {}


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def extract_product_images(product_url: str) -> list[str]:
    if not product_url:
        return []
    if product_url in PRODUCT_IMAGE_CACHE:
        return PRODUCT_IMAGE_CACHE[product_url]

    images: list[str] = []
    try:
        request = Request(product_url, headers={"User-Agent": "ProductStore-RAG/1.0"})
        with urlopen(request, timeout=6) as response:
            html = response.read().decode("utf-8", errors="ignore")

        for pattern in (
            r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
            r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
        ):
            for match in re.findall(pattern, html, flags=re.IGNORECASE):
                images.append(urljoin(product_url, unescape(match)))

        for script in re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            try:
                data = json.loads(unescape(script))
            except json.JSONDecodeError:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict) or item.get("@type") != "Product":
                    continue
                image_value = item.get("image")
                if isinstance(image_value, str):
                    images.append(urljoin(product_url, image_value))
                elif isinstance(image_value, list):
                    images.extend(urljoin(product_url, str(image)) for image in image_value)
    except Exception:
        images = []

    unique_images = list(dict.fromkeys(images))[:5]
    PRODUCT_IMAGE_CACHE[product_url] = unique_images
    return unique_images


def product_cards_for_question(question: str) -> list[dict[str, object]]:
    products: list[dict[str, object]] = []
    for item in search_context(question, top_k=4):
        metadata = item["metadata"]
        if metadata.get("doc_type") != "product":
            continue

        source_url = str(metadata.get("source_url") or "")
        images = extract_product_images(source_url)
        if not images:
            continue

        products.append(
            {
                "name": metadata.get("name"),
                "price": metadata.get("price_text"),
                "category": metadata.get("category"),
                "url": source_url,
                "images": images,
            }
        )
        if len(products) == 2:
            break
    return products


class ProductStoreHandler(BaseHTTPRequestHandler):
    def do_HEAD(self) -> None:
        self._serve_static(send_body=False)

    def do_GET(self) -> None:
        self._serve_static(send_body=True)

    def _serve_static(self, send_body: bool) -> None:
        path = unquote(self.path.split("?", 1)[0])
        if path == "/":
            path = "/index.html"

        file_path = (STATIC_DIR / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())):
            self.send_error(403)
            return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return

        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(file_path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if send_body:
            self.wfile.write(content)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length) or b"{}")
            question = str(payload.get("message", "")).strip()
            if not question:
                self._send_json({"answer": "Savolingizni yozing, sizga yordam beraman."}, status=400)
                return

            answer = rag_answer(question)
            products = product_cards_for_question(question)
            self._send_json({"answer": answer, "products": products})
        except Exception as exc:
            self._send_json(
                {"answer": f"Xatolik yuz berdi: {exc}"},
                status=500,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[server] {self.address_string()} - {format % args}")

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), ProductStoreHandler)
    print(f"ProductStore UI: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
