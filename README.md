## 1) What this is

A tiny end-to-end “PDF → OCR → bounding boxes overlay” demo.

- `index.html`: UI (upload PDF, render pages, draw/hover/select boxes)
- `server.py`: local web server + **proxy** to Nanonets (avoids browser CORS and keeps the API key out of the frontend)
- `.env`: holds `NANONETS_API_KEY`

---

## 2) How it works (end to end)

- **Upload PDF (browser)**: you pick a `.pdf` in the UI.
- **Render PDF pages (browser)**: PDF.js renders the current page into a canvas (`#pdf-canvas`).
- **Run OCR (browser → local server)**:
  - The UI sends the *raw PDF file* as `multipart/form-data` to `POST /api/ocr`.
- **Proxy to Nanonets (local server → Nanonets)**:
  - `server.py` forwards that multipart body to `https://extraction-api.nanonets.com/api/v1/extract/sync`
  - It adds `Authorization: Bearer <NANONETS_API_KEY>` from `.env`
  - It requests word-level boxes via `include_metadata=bounding_boxes_word`
- **Receive OCR results (browser)**:
  - The UI groups returned elements by `bounding_box.page` into:
    - `ocrResults[pageNum] = [{ text, x, y, w, h, confidence }, ...]`
  - Coordinates are expected to be **normalized**: \(x,y,w,h \in [0,1]\).
- **Overlay boxes (browser)**:
  - A second canvas (`#overlay-canvas`) sits absolutely on top of the PDF canvas.
  - For each box, the UI converts normalized coords to canvas pixels:
    - `pxX = x * canvasWidth`, `pxY = y * canvasHeight`, `pxW = w * canvasWidth`, `pxH = h * canvasHeight`
  - Hover/click uses the same math (hit-testing) to show the correct tooltip text and highlight selection.

---

## 3) How to run locally

1. Ensure `.env` exists:

```bash
echo "NANONETS_API_KEY=YOUR_KEY" > .env
```

2. Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install requests
```

3. Start the local server:

```bash
.venv/bin/python3 server.py
```

4. Open the app:
- `http://localhost:8765`

---

## Assumptions (current MVP)

- **No user/session concept**: there is no authentication or session persistence; a refresh loses all OCR results in memory.
- **No database/storage**: extracted results are not stored server-side (only kept in browser memory, and optionally exportable as JSON).
- **Small PDFs only**: the MVP uses the **sync** extraction endpoint, assuming documents are small enough to complete quickly.

---

## Improvements / Next steps

- **Async processing for larger PDFs**:
  - Upload the PDF to **S3** (or any blob store) first.
  - Use the **async** extraction flow and **poll** results (e.g. every 3 seconds) until completed.
- **Streaming UX**:
  - Use the **stream** endpoint and keep an **SSE** connection open to show partial/real-time results as they arrive.
- **Persistence**:
  - Store OCR results in a DB keyed by a document/job id so refreshes and sharing links work.

