# PDF Utilities – Phase 1 (Merge & Compress)

Professional PDF tools (Phase 1): **Merge PDFs** and **Compress PDF**.
Frontend: **React (CRA)** • Backend: **FastAPI (Python)**

> Status: **Local development** (frontend + backend) with a single command runner.

---

## ✨ Features (Phase 1)

* **Merge PDFs** – upload 2+ PDFs and get a single merged file.
* **Compress PDF** – reduce PDF size via:

  * Lightweight compression (PyPDF2; default)
  * Real compression using **Ghostscript** (recommended for image-heavy PDFs)

---

## 🧱 Tech Stack

**Frontend**

* React (Create React App)
* lucide-react (icons)
* Fetch API

**Backend**

* FastAPI
* Uvicorn
* PyPDF2
* Ghostscript CLI for stronger compression

**Dev Experience**

* `concurrently` to run frontend + backend together

---

## 📁 Project Structure

```
andpdf.in/
├─ backend/
│  ├─ main.py
│  ├─ requirements.txt
│  ├─ run.py                # optional (python entry)
│  └─ .env                  # optional
├─ frontend/
│  ├─ src/
│  │  ├─ App.jsx
│  │  ├─ App.css
│  │  ├─ index.js
│  │  └─ index.css
│  ├─ public/index.html
│  ├─ package.json
│  └─ .env.example
└─ package.json             # root (concurrently scripts)
```

---

## 🚀 Getting Started (Local)

### 1) Clone & enter the project

```bash
git clone deepakkumar-m/andpdf.in.git
cd andpdf.in
```

### 2) Backend setup

```bash
cd backend
python -m venv venv
# macOS/Linux:
source venv/bin/activate
# Windows (PowerShell):
# .\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3) Frontend setup

```bash
cd ../frontend
npm install
```

Create `frontend/.env` (optional for local; defaults to localhost:8000):

```
REACT_APP_API_URL=http://localhost:8000
```

### 4) One-command dev runner (recommended)

At the **repo root** (`andpdf.in/`), create a root `package.json` if you don’t have one:

```json
{
  "name": "andpdf.in",
  "private": true,
  "scripts": {
    "start": "concurrently \"npm:frontend\" \"npm:backend\"",
    "frontend": "cd frontend && npm start",
    "backend": "cd backend && python run.py"
  },
  "devDependencies": {
    "concurrently": "^9.0.0"
  }
}
```

Install root dev deps:

```bash
npm install
```

Start everything:

```bash
npm start
```

* Frontend: [http://localhost:3000](http://localhost:3000)
* Backend health: [http://localhost:8000/api/health](http://localhost:8000/api/health)

> **Tip:** If you prefer not to use `run.py`, change the backend script to:
>
> ```json
> "backend": "cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"
> ```

---

## 🔌 API Endpoints

### Health

```
GET /api/health
```

**Response**

```json
{ "status": "healthy", "timestamp": "2025-11-10T14:25:00.123456" }
```

### Merge PDFs

```
POST /api/pdf/merge
FormData: files (repeat) [min 2 PDFs]
Returns: application/pdf (merged file)
```

**curl**

```bash
curl -X POST "http://localhost:8000/api/pdf/merge" \
  -F "files=@/path/to/one.pdf" \
  -F "files=@/path/to/two.pdf" \
  -o merged.pdf
```

### Compress PDF

```
POST /api/pdf/compress?quality=85
FormData: file (single PDF)
Returns: application/pdf (compressed file)
Response headers (exposed to browser):
  - X-Original-Size
  - X-Compressed-Size
  - X-Reduction-Percentage
  - X-Quality-Setting
```

**curl**

```bash
curl -X POST "http://localhost:8000/api/pdf/compress?quality=85" \
  -F "file=@/path/to/input.pdf" \
  -D - \
  -o compressed.pdf
```

---

## 🖥️ Frontend (What it does)

* **Tabs:** Merge PDFs / Compress PDF
* **Drag & Drop** or click to upload
* **Validation:** file type, size (50MB)
* **Compression slider (1–100)** → forwarded to backend
* **Download** of result with filename from `Content-Disposition`
* **Stats** (Original/Compressed/Reduced %) via response headers, with fallback to sizes in the browser if headers aren’t accessible

---

## 🌐 CORS (Local)

Backend enables CORS for these origins by default:

* `http://localhost:3000`
* `http://127.0.0.1:3000`
* `http://localhost:5173`
* `http://127.0.0.1:5173`

And **exposes**:

```
Content-Disposition,
X-Original-Size,
X-Compressed-Size,
X-Reduction-Percentage,
X-Quality-Setting
```

---

## 📦 Real Compression (Recommended)

`PyPDF2`’s compression is minimal. For **real size reduction**, install **Ghostscript** and use the enhanced backend path:

### Install Ghostscript

* macOS: `brew install ghostscript`
* Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y ghostscript`
* Windows:

  * Chocolatey: `choco install ghostscript`
  * Scoop: `scoop install ghostscript`

Verify:

```bash
gs -v
```

The backend detects `gs` automatically and uses it if available, mapping the UI slider to practical presets:

* `/screen` (low dpi, smallest)
* `/ebook`
* `/printer`
* `/prepress` (highest quality)

> Expect large reductions (40–80%) for **image-heavy/scanned PDFs**.
> Vector/text-based PDFs may not shrink much.

---

## 🧪 Local Testing Cheat-Sheet

**Backend only**

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# open http://localhost:8000/docs
```

**Frontend only**

```bash
cd frontend
npm start
```

**Both (recommended)**

```bash
# from repo root
npm start
```

<img width="2670" height="2058" alt="image" src="https://github.com/user-attachments/assets/2d0b9685-3b6c-481e-b4c9-4f1f81dd9bd5" />

---

## 🛠️ Troubleshooting

* **Frontend “Failed to fetch”**

  * Backend not running, wrong port, or CORS/preflight blocked.
  * Check [http://localhost:8000/api/health](http://localhost:8000/api/health) in the browser.
  * Ensure CORS origins match your frontend URL.

* **Headers show 0 Bytes / 0.00%**

  * Browser can’t read headers → ensure backend CORS has `expose_headers` (listed above).
  * Frontend falls back to using `File.size` and `blob.size`.

* **“Attribute app not found in module main”**

  * Run uvicorn from **backend folder**, or use `backend.main:app` from root.
  * Make sure `app = FastAPI(...)` exists at top level in `main.py`.

* **Compression barely changes size**

  * Install Ghostscript. Image-heavy PDFs will shrink significantly.

* **File too large**

  * Default file limit is 50MB (frontend check). Adjust in frontend and/or add server-side validation if needed.

---

## 🔒 Notes & Safety

* Uploaded files are processed in OS temp dir and periodically cleaned (older than 1 hour).
* No files are stored permanently by the backend.
* **Do not** expose this build publicly as-is—add auth/rate limits if required.

---

## 🗺️ Roadmap (Next Phases)

* Split PDF (by pages/range)
* Rotate pages
* Add watermark
* Reorder pages (drag-and-drop)
* OCR for scanned PDFs (e.g., Tesseract)
* Deploy (Render/Netlify/Fly.io) with HTTPS and CORS hardening

---

## 📜 License

MIT (or your preferred license)

---

## 🙌 Credits

Built by Deepak ❤️ using React, FastAPI, and Ghostscript for reliable PDF tooling.
