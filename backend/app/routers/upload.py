import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document
from app.schemas import UploadResponse
from app.parsing import parse_pdf_and_populate_metrics

router = APIRouter()

# Directory to store uploaded PDFs
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/balance-sheet", response_model=UploadResponse)
async def upload_balance_sheet(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF balance sheet/annual report.
    Validates the file, saves it, creates a Document record, and parses it.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("application/pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )
    
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="File must have .pdf extension"
        )
    
    try:
        # Generate unique filename
        file_uuid = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        storage_filename = f"{file_uuid}{file_extension}"
        storage_path = UPLOAD_DIR / storage_filename
        
        # Save file
        with open(storage_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Get absolute path for storage in DB
        absolute_path = str(storage_path.resolve())
        
        # Create Document record
        doc = Document(
            filename=file.filename,
            storage_path=absolute_path,
            company_name=None,  # Will be filled by parser
            fiscal_year=None,   # Will be filled by parser
            company_code=None
        )
        
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # Parse PDF and populate metrics
        try:
            parse_pdf_and_populate_metrics(doc, db)
            # Refresh to get updated company_name and fiscal_year
            db.refresh(doc)
        except Exception as e:
            # Log error but don't fail the upload
            # The document is created, parsing can be retried later if needed
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Error parsing PDF: {e}")
        
        return UploadResponse(
            document_id=doc.id,
            company_name=doc.company_name,
            fiscal_year=doc.fiscal_year
        )
    
    except Exception as e:
        # Clean up file if document creation failed
        if 'storage_path' in locals() and storage_path.exists():
            storage_path.unlink()
        
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error uploading file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing upload: {str(e)}"
        )

