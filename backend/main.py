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
    allow_origins=["*"
    ],
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
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend_build")

if os.path.exists(FRONTEND_DIR):
    static_dir = os.path.join(FRONTEND_DIR, "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print("⚠️ Warning: frontend_build directory not found!")

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
        raise HTTPException(status_code=400, detail="At least 2 PDF files are required for merging")

    output_filename = f"merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = os.path.join(UPLOAD_DIR, output_filename)

    merger = PyPDF2.PdfMerger()
    try:
        for file in files:
            if not file.filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF")
            pdf_content = await file.read()
            merger.append(io.BytesIO(pdf_content))
        with open(output_path, "wb") as f:
            merger.write(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        merger.close()

    return FileResponse(output_path, media_type="application/pdf", filename=output_filename)

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
    original_size = len(content)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_in:
        tmp_in.write(content)
        in_path = tmp_in.name

    out_name = f"compressed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    out_path = os.path.join(UPLOAD_DIR, out_name)

    preset, downsample_flags = _gs_args_for_quality(quality)
    cmd = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-dPDFSETTINGS={preset}",
        *downsample_flags,
        f"-sOutputFile={out_path}",
        in_path,
    ]

    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Ghostscript failed: {e}")
    finally:
        os.remove(in_path)

    compressed_size = os.path.getsize(out_path)
    reduction = ((original_size - compressed_size) / original_size * 100) if original_size else 0

    return FileResponse(
        out_path,
        media_type="application/pdf",
        filename=out_name,
        headers={
            "Content-Disposition": f"attachment; filename={out_name}",
            "X-Original-Size": str(original_size),
            "X-Compressed-Size": str(compressed_size),
            "X-Reduction-Percentage": f"{reduction:.2f}",
        },
    )

# =====================
# 🔹 Run
# =====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
