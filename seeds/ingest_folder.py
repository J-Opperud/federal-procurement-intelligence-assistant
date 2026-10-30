"""Standalone script to ingest and index files from a local folder path."""

from pathlib import Path
from app.database import SessionLocal
from app.models import ProcurementNotice
from app.services.source_ingestion import extract_document_text
from app.services.chroma_evidence_service import index_procurement_notice

def ingest_from_folder(folder_path: str = "seeds/samples"):
    target_dir = Path(folder_path)
    if not target_dir.exists():
        print(f"❌ Directory not found: {target_dir.absolute()}")
        return

    db = SessionLocal()
    try:
        print(f"📂 Scanning folder: {target_dir.absolute()}")
        count = 0
        
        for file_path in target_dir.glob("*.*"):
            if file_path.suffix.lower() in {".txt", ".md", ".pdf"}:
                try:
                    # 1. Read and extract text using your native extraction function
                    extracted_text = extract_document_text(file_path)
                    
                    sam_id = f"LOCAL-{file_path.stem.upper()}"
                    
                    # 2. Check if notice already exists to prevent duplicates
                    notice = db.query(ProcurementNotice).filter_by(sam_notice_id=sam_id).first()
                    if not notice:
                        notice = ProcurementNotice(
                            sam_notice_id=sam_id,
                            title=file_path.stem.replace("_", " ").title(),
                            notice_type="Solicitation",
                            department="Local File Ingestion",
                            description=extracted_text,
                            source_url=f"local://{file_path.name}"
                        )
                        db.add(notice)
                        db.commit()
                        db.refresh(notice)
                    
                    # 3. Pass through your existing vector indexing pipeline
                    index_procurement_notice(db, notice)
                    print(f"✅ Successfully read, stored, and indexed: {file_path.name}")
                    count += 1
                except Exception as e:
                    db.rollback()
                    print(f"⚠️ Failed to process {file_path.name}: {e}")
                    
        print(f"🎉 Ingestion complete! Processed {count} files.")
    finally:
        db.close()

if __name__ == "__main__":
    ingest_from_folder()