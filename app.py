"""
app.py - Deployable FastAPI Web Application Server
Provides REST API endpoints and web UI for real-time PII redaction and document download.
"""

import os
import shutil
import tempfile
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pii_redactor import PIIRedactor
from docx_redactor import DOCXRedactor
from evaluate import PIIEvaluator

app = FastAPI(
    title="PII Redaction & Anonymization Web Service",
    description="Enterprise API for redacting PII in text and DOCX documents.",
    version="2.0.0"
)

# Serve static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Shared redactor instances
redactor_synth = PIIRedactor(mode="SYNTHETIC")
redactor_mask = PIIRedactor(mode="MASK")
evaluator = PIIEvaluator()

class RedactTextRequest(BaseModel):
    text: str
    mode: Optional[str] = "SYNTHETIC"

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/redact-text")
async def redact_text_endpoint(req: RedactTextRequest):
    redactor = redactor_mask if req.mode == "MASK" else redactor_synth
    redacted_text, entities = redactor.redact_text(req.text)
    
    entity_list = [
        {
            "entity_type": item.entity_type,
            "text": item.text,
            "start": item.start,
            "end": item.end,
            "score": item.score,
            "replacement": item.replacement
        }
        for item in entities
    ]
    return {
        "redacted_text": redacted_text,
        "entities": entity_list
    }

@app.post("/api/redact-file")
async def redact_file_endpoint(file: UploadFile = File(...), mode: str = Form("SYNTHETIC")):
    redactor = redactor_mask if mode == "MASK" else redactor_synth
    docx_redactor = DOCXRedactor(redactor)

    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in (".docx", ".txt"):
        raise HTTPException(status_code=400, detail="Only .docx and .txt files are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_in:
        shutil.copyfileobj(file.file, temp_in)
        temp_in_path = temp_in.name

    temp_out_path = temp_in_path.replace(suffix, f"_redacted{suffix}")

    try:
        if suffix == ".docx":
            docx_redactor.redact_document(temp_in_path, temp_out_path)
        else:
            with open(temp_in_path, "r", encoding="utf-8") as f:
                content = f.read()
            redacted_content, _ = redactor.redact_text(content)
            with open(temp_out_path, "w", encoding="utf-8") as f:
                f.write(redacted_content)

        return FileResponse(
            path=temp_out_path,
            filename=f"Redacted_{file.filename}",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document" if suffix == ".docx" else "text/plain"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/evaluation-metrics")
async def get_evaluation_metrics():
    return evaluator.run_evaluation()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
