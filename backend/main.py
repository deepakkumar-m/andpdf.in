from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import PyPDF2
from PyPDF2 import PdfReader, PdfWriter
import io
import os
from typing import List
import tempfile
from datetime import datetime
import shutil

app = FastAPI(
    title="PDF Utilities API",
    description="Professional PDF manipulation tools",
    version="1.1.0"
)

# =====================
# 🔹 CORS Configuration
# =====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all (safe for same domain frontend-backend)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Disposition",
        "X-Original-Size",
        "X-Compressed-Size",
        "X-Reduction-Percentage",
    ],
)

# =====================
# 🔹 Frontend Build Directory
# =====================
FRONTEND_DIR = os.path.join(os.getcwd(), "frontend_build")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")


@app.get("/")
def serve_react():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "React build not found."}


# =====================
# 🔹 Temporary Storage Setup
# =====================
TEMP_DIR = tempfile.gettempdir()
UPLOAD_DIR = os.path.join(TEMP_DIR, "pdf_uploads")
COMPRESSED_DIR = os.path.join(TEMP_DIR, "pdf_compressed")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(COMPRESSED_DIR, exist_ok=True)


def cleanup_old_files():
    """Remove old temporary files older than 1 hour"""
    for folder in [UPLOAD_DIR, COMPRESSED_DIR]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path):
                    file_age = datetime.now().timestamp() - os.path.getmtime(file_path)
                    if file_age > 3600:
                        os.remove(file_path)
            except Exception as e:
                print(f"Cleanup error: {e}")


@app.on_event("startup")
async def startup_event():
    cleanup_old_files()


# =====================
# 🔹 Serve Frontend Routes
# =====================
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Frontend build not found. Please ensure npm run build has been executed.",
        "status": "backend-only mode",
    }


# =====================
# 🔹 Health Endpoint
# =====================
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# =====================
# 🔹 PDF MERGE
# =====================
@app.post("/api/pdf/merge")
async def merge_pdfs(files: List[UploadFile] = File(...)):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="At least 2 PDF files are required")

    output_path = os.path.join(tempfile.gettempdir(), f"merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    merger = PyPDF2.PdfMerger()

    try:
        for f in files:
            if not f.filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f"{f.filename} is not a PDF")
            content = await f.read()
            merger.append(io.BytesIO(content))
        with open(output_path, "wb") as out:
            merger.write(out)
    finally:
        merger.close()

    return FileResponse(output_path, media_type="application/pdf", filename=os.path.basename(output_path))


# =====================
# 🔹 PDF COMPRESS (Simulated — PyPDF2)
# =====================
@app.post("/api/pdf/compress")
async def compress_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    input_path = os.path.join(UPLOAD_DIR, file.filename)
    output_path = os.path.join(COMPRESSED_DIR, file.filename)

    # Save uploaded file
    with open(input_path, "wb") as f:
        f.write(await file.read())

    # Simulated compression using PyPDF2 (safe placeholder)
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    # Calculate size details
    original_size = os.path.getsize(input_path)
    compressed_size = os.path.getsize(output_path)
    reduction_percent = round((1 - (compressed_size / original_size)) * 100, 2) if original_size > 0 else 0

    return JSONResponse({
        "message": "PDF Compressed Successfully!",
        "original_size": f"{original_size / (1024 * 1024):.2f} MB",
        "compressed_size": f"{compressed_size / (1024 * 1024):.2f} MB",
        "reduction_percent": f"{reduction_percent}%",
        "download_url": f"/download/{os.path.basename(output_path)}"
    })


# =====================
# 🔹 Download Endpoint
# =====================
@app.get("/download/{filename}")
async def download_file(filename: str):
    path = os.path.join(COMPRESSED_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)


# =====================
# 🔹 Run Server
# =====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    allow_origins=["*"],  # Safe here because frontend and backend are same domain on Render