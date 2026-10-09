# ProductStore AI Assistant

ProductStore uchun RAG asosidagi AI yordamchi. Assistant do'kon ma'lumotlari va mahsulot chunklari asosida mijoz savollariga javob beradi, kerakli productlarni topadi va UI orqali chat ko'rinishida ishlaydi.

## Nima qilindi

- `data/` ichidagi JSONL ma'lumotlar tekshirildi.
- 451 ta chunk ChromaDB vector bazasiga embedding qilindi.
- Claude API uchun alohida wrapper yozildi.
- RAG orkestratori yaratildi: savol -> ChromaDB search -> context -> Claude javobi.
- Do'kon manzili, ish vaqti va "hozir ochiqmi?" kabi savollar uchun maxsus handlerlar qo'shildi.
- Sotuvchidek muloyim, qisqa va foydali javob beradigan system prompt yozildi.
- Product tanlanganda UI'da product card va rasm ko'rsatish qo'shildi.
- Oddiy HTML/CSS/JS chat UI yaratildi.
- Local server `3000` portda ishlaydigan qilindi.
- Ngrok orqali public demo qilish yo'li sinab ko'rildi.

## Texnologiyalar

- **Python 3.14** - backend va RAG orkestratsiya.
- **Anthropic Claude API** - yakuniy javoblarni generatsiya qilish.
- **ChromaDB** - local vector database.
- **Chroma default embedding modeli** - `all-MiniLM-L6-v2` ONNX varianti.
- **HTML / CSS / JavaScript** - chat UI.
- **Python `http.server`** - yengil local web server.
- **python-dotenv** - `.env` sozlamalarini o'qish.
- **ngrok** - local serverni public link orqali ulash.

## Fayllar

- `chat_to_claude.py` - Claude API bilan ishlaydigan wrapper.
- `main.py` - RAG logikasi, ChromaDB qidiruv, vaqt/ish vaqti handlerlari.
- `embed_to_chroma.py` - JSONL chunklarni ChromaDB'ga embedding qilib yuklash.
- `server.py` - local HTTP server va `/api/chat` endpoint.
- `static/index.html` - chat sahifasi.
- `static/styles.css` - ProductStore uslubidagi UI.
- `static/app.js` - frontend chat logikasi.
- `data/dokon-info.jsonl` - do'kon haqidagi ma'lumotlar.
- `data/product-chunks-pandas.jsonl` - mahsulot chunklari.

## `.env`

`.env` fayl gitga qo'shilmaydi. Kerakli qiymatlar:

```env
ANTHROPIC_API_KEY=your_api_key_here
DEFAULT_MODEL=claude-sonnet-5-5
DEFAULT_MAX_TOKENS=1500
```

## O'rnatish

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## ChromaDB bazani yaratish

```bash
.venv/bin/python embed_to_chroma.py --reset
```

Bu buyruq `data/` ichidagi JSONL fayllarni o'qib, `chroma_db/` papkasiga vector bazani yaratadi.

## Local UI ni ishga tushirish

```bash
.venv/bin/python server.py
```

Brauzerda oching:

```text
http://127.0.0.1:3000
```

## Ngrok orqali ulash

Local server ishlab turganda boshqa terminalda:

```bash
ngrok http 3000
```

Ngrok bergan `https://...ngrok-free.app` link orqali demo ko'rish mumkin. Free ngrok birinchi kirishda warning page chiqaradi; `Visit Site` bosilsa sayt ochiladi.

## Eslatma

- `.env`, `.venv/`, `.cache/`, `chroma_db/` va Python cache fayllar gitga kiritilmaydi.
- `chroma_db/` local generated baza. Yangi muhitda qayta yaratish uchun `embed_to_chroma.py --reset` ishlatiladi.
- Product rasmlari product sahifasidagi metadata orqali olinadi, shuning uchun internet kerak bo'lishi mumkin.
