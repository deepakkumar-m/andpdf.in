from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import PyPDF2
import io
import os
from typing import List
import tempfile
from datetime import datetime
import shutil
import subprocess
import json

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
    allow_origins=["*"],
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


# =====================
# 🔹 Temporary Storage
# =====================
TEMP_DIR = tempfile.gettempdir()
UPLOAD_DIR = os.path.join(TEMP_DIR, "pdf_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def cleanup_old_files():
    """Remove old temporary files (>1 hour old)"""
    now = datetime.now().timestamp()
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        try:
            if os.path.isfile(file_path):
                file_age = now - os.path.getmtime(file_path)
                if file_age > 3600:  # older than 1 hour
                    os.remove(file_path)
        except Exception as e:
            print(f"Cleanup error: {e}")


@app.on_event("startup")
async def startup_event():
    cleanup_old_files()


# =====================
# 🔹 Serve Frontend (SPA fallback)
# =====================
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Frontend build not found. Please ensure `npm run build` has been executed.",
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

    output_filename = f"merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = os.path.join(UPLOAD_DIR, output_filename)
    merger = PyPDF2.PdfMerger()

    temp_files = []
    try:
        for f in files:
            if not f.filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f"{f.filename} is not a PDF")
            content = await f.read()
            temp_file = io.BytesIO(content)
            merger.append(temp_file)
            temp_files.append(temp_file)
        with open(output_path, "wb") as out:
            merger.write(out)
    finally:
        merger.close()
        for tf in temp_files:
            tf.close()

    return FileResponse(output_path, media_type="application/pdf", filename=output_filename)


# =====================
# 🔹 PDF COMPRESS (ULTRA-RELIABLE VERSION)
# =====================
@app.post("/api/pdf/compress")
async def compress_pdf(file: UploadFile = File(...), level: int = 0):
    """
    Compress PDF using Ghostscript with fallback methods.
    Valid levels:
        0: /screen     → Maximum compression (72 DPI)
        1: /ebook      → Balanced compression (150 DPI)
        2: /printer    → High quality (300 DPI)
        3: /prepress   → Highest quality (300+ DPI)
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    input_path = os.path.join(UPLOAD_DIR, f"input_{timestamp}.pdf")
    output_path = os.path.join(UPLOAD_DIR, f"compressed_{timestamp}.pdf")
    fallback_path = os.path.join(UPLOAD_DIR, f"fallback_{timestamp}.pdf")

    # Save uploaded file
    content = await file.read()
    with open(input_path, "wb") as f:
        f.write(content)

    # Map level to parameters
    quality_settings = {
        0: {
            "preset": "/screen",
            "color_res": 72,
            "gray_res": 72,
            "mono_res": 72,
            "jpeg_q": 10,
            "downsample": True
        },
        1: {
            "preset": "/ebook",
            "color_res": 150,
            "gray_res": 150,
            "mono_res": 150,
            "jpeg_q": 50,
            "downsample": True
        },
        2: {
            "preset": "/printer",
            "color_res": 300,
            "gray_res": 300,
            "mono_res": 300,
            "jpeg_q": 75,
            "downsample": False
        },
        3: {
            "preset": "/prepress",
            "color_res": 300,
            "gray_res": 300,
            "mono_res": 300,
            "jpeg_q": 90,
            "downsample": False
        }
    }

    if level not in quality_settings:
        raise HTTPException(status_code=400, detail="Compression level must be 0, 1, 2, or 3")

    settings = quality_settings[level]

    # Locate Ghostscript binary
    gs = shutil.which("gs") or shutil.which("gswin32c") or shutil.which("gswin64c")
    if not gs:
        raise HTTPException(
            status_code=500,
            detail="Ghostscript not found. Please install Ghostscript and add it to your system PATH."
        )

    # Build primary Ghostscript command with explicit parameters
    cmd = [
        gs,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.7",
        f"-dPDFSETTINGS={settings['preset']}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        "-dEmbedAllFonts=true",
        "-dSubsetFonts=true",
        "-dAutoRotatePages=/None",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dCompressPages=true",
        "-dUseFlateCompression=true",
        f"-dColorImageResolution={settings['color_res']}",
        f"-dGrayImageResolution={settings['gray_res']}",
        f"-dMonoImageResolution={settings['mono_res']}",
        f"-dJPEGQ={settings['jpeg_q']}",
        f"-sOutputFile={output_path}",
        input_path,
    ]

    # Add downsample flags if needed
    if settings['downsample']:
        cmd.extend([
            "-dDownsampleColorImages=true",
            "-dDownsampleGrayImages=true",
            "-dDownsampleMonoImages=true",
            "-dColorImageFilter=/DCTEncode",
            "-dGrayImageFilter=/DCTEncode",
            "-dMonoImageFilter=/CCITTFaxEncode",
        ])

    # Try primary compression
    compression_success = False
    stderr_output = ""
    
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            timeout=60  # 60 second timeout
        )
        stderr_output = result.stderr.decode("utf-8", errors="ignore")
        compression_success = True
    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
        print(f"Primary compression failed: {stderr_output}")
    except Exception as e:
        stderr_output = str(e)
        print(f"Primary compression exception: {stderr_output}")

    # Fallback method if primary fails or produces no reduction
    if not compression_success or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        print("Using fallback compression method")
        
        fallback_cmd = [
            gs,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/screen",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dEmbedAllFonts=true",
            "-dSubsetFonts=true",
            "-dAutoRotatePages=/None",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dCompressPages=true",
            "-dUseFlateCompression=true",
            "-dDownsampleColorImages=true",
            "-dDownsampleGrayImages=true",
            "-dDownsampleMonoImages=true",
            "-dColorImageResolution=72",
            "-dGrayImageResolution=72",
            "-dMonoImageResolution=72",
            "-dColorImageFilter=/DCTEncode",
            "-dGrayImageFilter=/DCTEncode",
            "-dMonoImageFilter=/CCITTFaxEncode",
            "-dJPEGQ=10",
            f"-sOutputFile={fallback_path}",
            input_path,
        ]
        
        try:
            subprocess.run(fallback_cmd, check=True, stderr=subprocess.PIPE, timeout=60)
            if os.path.exists(fallback_path) and os.path.getsize(fallback_path) > 0:
                # Use fallback file
                output_path = fallback_path
                compression_success = True
        except Exception as e:
            fallback_error = str(e)
            print(f"Fallback compression failed: {fallback_error}")

    if not compression_success or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise HTTPException(
            status_code=500, 
            detail=f"Compression failed after all attempts. Ghostscript error: {stderr_output}"
        )

    # Verify compression actually happened
    orig_size = os.path.getsize(input_path)
    comp_size = os.path.getsize(output_path)
    
    # If compression failed (output >= input), try one last aggressive method
    if comp_size >= orig_size and level < 2:
        print(f"Compression ineffective (output {comp_size} >= input {orig_size}), trying aggressive method")
        aggressive_cmd = [
            gs,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dEmbedAllFonts=false",  # Don't embed fonts
            "-dSubsetFonts=false",
            "-dAutoRotatePages=/None",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dCompressPages=true",
            "-dUseFlateCompression=true",
            "-dDownsampleColorImages=true",
            "-dDownsampleGrayImages=true",
            "-dDownsampleMonoImages=true",
            "-dColorImageResolution=50",
            "-dGrayImageResolution=50",
            "-dMonoImageResolution=50",
            "-dColorImageFilter=/DCTEncode",
            "-dGrayImageFilter=/DCTEncode",
            "-dMonoImageFilter=/CCITTFaxEncode",
            "-dJPEGQ=5",
            "-dPDFSETTINGS=/screen",
            "-dColorConversionStrategy=/RGB",
            "-dProcessColorModel=/DeviceRGB",
            f"-sOutputFile={output_path}",
            input_path,
        ]
        
        try:
            subprocess.run(aggressive_cmd, check=True, stderr=subprocess.PIPE, timeout=60)
            new_comp_size = os.path.getsize(output_path)
            if new_comp_size < comp_size:
                comp_size = new_comp_size
                print(f"Aggressive compression succeeded: {orig_size} -> {comp_size}")
        except Exception as e:
            print(f"Aggressive compression failed: {str(e)}")

    # Calculate reduction
    reduction = max(0.0, 100 * (1 - comp_size / orig_size)) if orig_size > 0 else 0.0
    
    # If reduction is negligible (<5%) and level is aggressive, force a minimum reduction
    if reduction < 5 and level < 2:
        # Log the issue but don't fail
        print(f"Warning: Minimal compression achieved ({reduction:.2f}%) for level {level}")

    headers = {
        "X-Original-Size": str(orig_size),
        "X-Compressed-Size": str(comp_size),
        "X-Reduction-Percentage": f"{reduction:.2f}",
        "X-Quality-Setting": settings['preset'],
    }

    # Cleanup input file
    try:
        os.remove(input_path)
    except:
        pass

    output_filename = f"compressed_{os.path.splitext(file.filename)[0]}.pdf"
    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=output_filename,
        headers=headers
    )


# =====================
# 🔹 Run Server (for local dev)
# =====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)