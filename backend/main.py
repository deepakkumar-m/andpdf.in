from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import PyPDF2
from PIL import Image
import io
import os
from typing import List
import tempfile
from datetime import datetime
import shutil
import subprocess

app = FastAPI(
    title="PDF Utilities API",
    description="Professional PDF manipulation tools",
    version="1.0.0"
)

# =====================
# 🔹 CORS Configuration
# =====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Safe here because frontend and backend are same domain on Render
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Disposition",
        "X-Original-Size",
        "X-Compressed-Size",
        "X-Reduction-Percentage",
        "X-Quality-Setting",
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

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
# =====================
# 🔹 Temporary Storage
# =====================
TEMP_DIR = tempfile.gettempdir()
UPLOAD_DIR = os.path.join(TEMP_DIR, "pdf_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def cleanup_old_files():
    """Remove old temporary files"""
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
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
# 🔹 Serve Frontend
# =====================
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """
    Serve the React frontend for any route (/, /merge, /compress, etc.)
    """
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
# 🔹 PDF COMPRESS
# =====================
def _gs_args_for_quality(quality: int):
    if quality <= 25:
        preset = "/screen"; dpi = 72; jpegq = 50
    elif quality <= 60:
        preset = "/ebook"; dpi = 120; jpegq = 60
    elif quality <= 85:
        preset = "/printer"; dpi = 200; jpegq = 75
    else:
        preset = "/prepress"; dpi = 300; jpegq = 85
    return preset, [
        "-dDownsampleColorImages=true",
        f"-dColorImageResolution={dpi}",
        "-dJPEGQ=" + str(jpegq)
    ]

@app.post("/api/pdf/compress")
async def compress_pdf(file: UploadFile = File(...), quality: int = 85):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    content = await file.read()
    input_path = os.path.join(tempfile.gettempdir(), "input.pdf")
    with open(input_path, "wb") as f:
        f.write(content)

    output_path = os.path.join(tempfile.gettempdir(), f"compressed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

    preset = "/ebook" if quality <= 60 else "/printer"
    cmd = [
        "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-dPDFSETTINGS={preset}",
        f"-sOutputFile={output_path}",
        input_path
    ]

    try:
        subprocess.check_call(cmd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compression failed: {e}")

    return FileResponse(output_path, media_type="application/pdf", filename=os.path.basename(output_path))
# =====================
# 🔹 Run
# =====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
