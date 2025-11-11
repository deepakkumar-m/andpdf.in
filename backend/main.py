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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(
    title="PDF Utilities API",
    description="Professional PDF manipulation tools",
    version="1.0.0"
)

# CORS configuration - adjust origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000","http://127.0.0.1:3000",
        "http://localhost:5173","http://127.0.0.1:5173",
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

# Optional: serve a built frontend if present. Supports either a top-level
# `frontend_build/` directory or the common `frontend/build/` created by
# `react-scripts build`. If no build is present, the API routes behave as before.
BUILD_DIR = None
_candidate_dirs = [
    os.path.join(os.path.dirname(__file__), '..', 'frontend_build'),
    os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build'),
]
for _d in _candidate_dirs:
    try:
        if os.path.isdir(_d):
            BUILD_DIR = os.path.abspath(_d)
            break
    except Exception:
        continue

if BUILD_DIR:
    # Serve static assets (js/css/images) under /static
    static_dir = os.path.join(BUILD_DIR, 'static')
    if os.path.isdir(static_dir):
        app.mount('/static', StaticFiles(directory=static_dir), name='static')


# Temporary directory for file operations
TEMP_DIR = tempfile.gettempdir()
UPLOAD_DIR = os.path.join(TEMP_DIR, "pdf_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def cleanup_old_files():
    """Clean up old temporary files"""
    try:
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                file_age = datetime.now().timestamp() - os.path.getmtime(file_path)
                if file_age > 3600:  # Delete files older than 1 hour
                    os.remove(file_path)
    except Exception as e:
        print(f"Cleanup error: {e}")

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    cleanup_old_files()

@app.get("/")
def read_root():
    """API root endpoint. If a frontend build exists, serve its index.html.
    Otherwise return the API description JSON."""
    # Serve built frontend if available
    try:
        if BUILD_DIR:
            index_path = os.path.join(BUILD_DIR, "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path)
    except Exception:
        # Fall back to API response if anything goes wrong
        pass

    return {
        "message": "PDF Utilities API",
        "version": "1.0.0",
        "status": "active",
        "tools": ["merge", "compress"],
        "docs": "/docs"
    }

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/pdf/merge")
async def merge_pdfs(files: List[UploadFile] = File(...)):
    """
    Merge multiple PDF files into a single PDF
    
    Parameters:
    - files: List of PDF files to merge (minimum 2 files)
    
    Returns:
    - Merged PDF file
    """
    # Validation
    if len(files) < 2:
        raise HTTPException(
            status_code=400, 
            detail="At least 2 PDF files are required for merging"
        )
    
    # Validate all files are PDFs
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' is not a PDF"
            )
    
    output_path = None
    temp_files = []
    
    try:
        merger = PyPDF2.PdfMerger()
        
        # Read and merge all PDFs
        for file in files:
            content = await file.read()
            
            # Validate PDF content
            try:
                pdf_file = io.BytesIO(content)
                PyPDF2.PdfReader(pdf_file)  # Validate
                pdf_file.seek(0)  # Reset position
                merger.append(pdf_file)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid PDF file '{file.filename}': {str(e)}"
                )
        
        # Create output file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"merged_{timestamp}.pdf"
        output_path = os.path.join(UPLOAD_DIR, output_filename)
        
        # Write merged PDF
        with open(output_path, 'wb') as output_file:
            merger.write(output_file)
        
        merger.close()
        
        # Return file
        return FileResponse(
            output_path,
            media_type='application/pdf',
            filename=output_filename,
            headers={
                "Content-Disposition": f"attachment; filename={output_filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error merging PDFs: {str(e)}"
        )
    finally:
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass

def _gs_args_for_quality(quality: int):
    """
    Map 1–100 slider to Ghostscript settings.
    Lower quality => stronger compression.
    """
    # Presets:
    # /screen (72dpi), /ebook (150dpi), /printer (300dpi), /prepress (300dpi, better quality)
    if quality <= 25:
        preset = "/screen";   dpi = 72;  jpegq = 50
    elif quality <= 60:
        preset = "/ebook";    dpi = 120; jpegq = 60
    elif quality <= 85:
        preset = "/printer";  dpi = 200; jpegq = 75
    else:
        preset = "/prepress"; dpi = 300; jpegq = 85

    # Explicit downsampling flags help more than the preset alone
    downsample_flags = [
        "-dDownsampleColorImages=true",
        "-dColorImageDownsampleType=/Average",
        f"-dColorImageResolution={dpi}",
        "-dDownsampleGrayImages=true",
        "-dGrayImageDownsampleType=/Average",
        f"-dGrayImageResolution={dpi}",
        "-dDownsampleMonoImages=true",
        "-dMonoImageDownsampleType=/Subsample",
        f"-dMonoImageResolution={dpi}",
        f"-dJPEGQ={jpegq}",
    ]

    return preset, downsample_flags

@app.post("/api/pdf/compress")
async def compress_pdf(file: UploadFile = File(...), quality: int = 85):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    if quality < 1 or quality > 100:
        raise HTTPException(status_code=400, detail="Quality must be between 1 and 100")

    if shutil.which("gs") is None:
        # Ghostscript not installed -> graceful fallback to PyPDF2 (tiny savings)
        # You can remove this branch once GS is installed everywhere you deploy.
        content = await file.read()
        original_size = len(content)
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid PDF file: {e}")
        writer = PyPDF2.PdfWriter()
        for page in reader.pages:
            page.compress_content_streams()
            writer.add_page(page)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"compressed_{ts}.pdf"
        out_path = os.path.join(UPLOAD_DIR, out_name)
        with open(out_path, "wb") as w:
            writer.write(w)
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
                "X-Quality-Setting": str(quality),
                "X-Note": "Ghostscript not found; used lightweight fallback.",
            },
        )

    # Ghostscript path
    content = await file.read()
    original_size = len(content)

    # write temp input
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_in:
        tmp_in.write(content)
        in_path = tmp_in.name

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"compressed_{ts}.pdf"
    out_path = os.path.join(UPLOAD_DIR, out_name)

    preset, downsample_flags = _gs_args_for_quality(quality)

    cmd = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
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
        try:
            os.remove(in_path)
        except Exception:
            pass

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
            "X-Quality-Setting": str(quality),
        },
    )

# Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )

