"""ProofLens AI — Documents API Router.

Implements streaming uploads, magic-byte checks, SHA-256 duplicate defense,
cross-workspace scope isolation, atomic worker claiming, and safe two-step deletion.
Protected by the Application-Level Access Passkey Gatekeeper.
"""

import hashlib
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.logging import logger
from app.core.security import verify_access_passkey
from app.repositories import document_repo, workspace_repo
from app.schemas.document import DocumentResponse, UploadBatchResponse
from app.services.storage.base import BaseStorageService
from app.services.storage.factory import get_storage_service

router = APIRouter(
    prefix="/workspaces/{workspace_id}/documents",
    tags=["Documents"],
    dependencies=[Depends(verify_access_passkey)],
)


@router.post(
    "/upload",
    response_model=UploadBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest PDF documents into a workspace",
)
async def upload_documents_endpoint(
    workspace_id: uuid.UUID,
    files: List[UploadFile] = File(..., description="Multipart PDF files to upload"),
    db: AsyncSession = Depends(get_db),
    storage: BaseStorageService = Depends(get_storage_service),
    settings: Settings = Depends(get_settings),
):
    """Secure streaming upload enforcing size boundaries, PDF magic bytes, and duplicate hashes."""
    # 1. Verify workspace scope
    workspace = await workspace_repo.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Workspace '{workspace_id}' does not exist.",
                "details": {"workspace_id": str(workspace_id)},
            },
        )

    # 2. Batch quantity limit check
    if len(files) > settings.MAX_UPLOAD_FILES_PER_BATCH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "BATCH_LIMIT_EXCEEDED",
                "message": f"Upload batch exceeds maximum allowed limit of {settings.MAX_UPLOAD_FILES_PER_BATCH} files.",
                "details": {
                    "max_allowed": settings.MAX_UPLOAD_FILES_PER_BATCH,
                    "received": len(files),
                },
            },
        )

    uploaded_documents: List[DocumentResponse] = []

    for upload_file in files:
        filename = Path(upload_file.filename or "document.pdf").name
        hasher = hashlib.sha256()
        accumulated_bytes = bytearray()
        chunk_size = 65_536  # 64 KB streaming chunks

        # 3. Stream byte chunks and enforce strict size ceiling
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            accumulated_bytes.extend(chunk)
            hasher.update(chunk)

            if len(accumulated_bytes) > settings.MAX_UPLOAD_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail={
                        "error_code": "FILE_TOO_LARGE",
                        "message": (
                            f"File '{filename}' exceeds maximum allowed size of "
                            f"{settings.MAX_UPLOAD_FILE_SIZE_BYTES} bytes."
                        ),
                        "details": {
                            "filename": filename,
                            "max_bytes": settings.MAX_UPLOAD_FILE_SIZE_BYTES,
                        },
                    },
                )

        file_bytes = bytes(accumulated_bytes)

        # 4. File-signature magic byte validation (must be PDF)
        if len(file_bytes) < 4 or not file_bytes[:1024].startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_PDF_SIGNATURE",
                    "message": f"File '{filename}' is not a valid PDF. File signature does not start with %PDF-.",
                    "details": {"filename": filename},
                },
            )

        content_hash = hasher.hexdigest()

        # 5. Check for existing duplicate in workspace
        existing_doc = await document_repo.get_document_by_hash(db, workspace_id, content_hash)
        if existing_doc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "DUPLICATE_DOCUMENT",
                    "message": f"Document '{filename}' with identical content hash already exists in this workspace.",
                    "details": {
                        "filename": filename,
                        "content_hash": content_hash,
                        "existing_document_id": str(existing_doc.id),
                    },
                },
            )

        # 6. Save physical file to storage
        doc_id = uuid.uuid4()
        storage_rel_path = f"workspaces/{workspace_id}/{doc_id}_{filename}"
        saved_storage_path = await storage.save_file(storage_rel_path, file_bytes)

        # 7. Create database record with collision defense
        try:
            doc_record = await document_repo.create_document(
                session=db,
                workspace_id=workspace_id,
                filename=filename,
                content_hash=content_hash,
                file_size_bytes=len(file_bytes),
                storage_path=saved_storage_path,
                status="pending",
            )
            uploaded_documents.append(doc_record)
        except IntegrityError:
            # Handle concurrent race condition tripping uq_workspace_content_hash
            await storage.delete_file(saved_storage_path)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "DUPLICATE_DOCUMENT",
                    "message": f"Concurrent duplicate detected: document '{filename}' was already uploaded.",
                    "details": {"filename": filename, "content_hash": content_hash},
                },
            )

    return UploadBatchResponse(
        uploaded=uploaded_documents,
        total_uploaded=len(uploaded_documents),
    )


@router.get(
    "",
    response_model=List[DocumentResponse],
    summary="List all documents in a workspace",
)
async def list_documents_endpoint(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all documents belonging to the specified workspace."""
    # Verify workspace exists
    workspace = await workspace_repo.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Workspace '{workspace_id}' not found.",
                "details": {"workspace_id": str(workspace_id)},
            },
        )
    return await document_repo.list_documents(db, workspace_id)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details by ID",
)
async def get_document_endpoint(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve document details strictly scoped to the workspace ID."""
    document = await document_repo.get_document_by_id(db, workspace_id, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Document '{document_id}' not found in workspace '{workspace_id}'.",
                "details": {
                    "workspace_id": str(workspace_id),
                    "document_id": str(document_id),
                },
            },
        )
    return document


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document using the safe two-step deletion protocol",
)
async def delete_document_endpoint(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: BaseStorageService = Depends(get_storage_service),
):
    """Delete document: locks row, commits database cascade, and purges physical file."""
    # 1. Lock row with SELECT ... FOR UPDATE
    document = await document_repo.lock_document_for_deletion(db, workspace_id, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Document '{document_id}' not found in workspace '{workspace_id}'.",
                "details": {
                    "workspace_id": str(workspace_id),
                    "document_id": str(document_id),
                },
            },
        )

    storage_path = document.storage_path

    # 2. Delete database record (triggers ON DELETE CASCADE and citations ON DELETE SET NULL)
    await document_repo.delete_document(db, document)

    # 3. Purge physical storage file
    storage_deleted = await storage.delete_file(storage_path)
    if not storage_deleted:
        # Relational state purged; log orphaned file for reconciliation without rolling back DB deletion
        logger.warning(
            f"Orphaned file detected: database record '{document_id}' purged but physical file "
            f"'{storage_path}' could not be deleted from storage."
        )

    return None


@router.post(
    "/{document_id}/retry",
    response_model=DocumentResponse,
    summary="Retry a failed document ingestion job",
)
async def retry_document_endpoint(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Manually retry ingestion for a failed document via atomic worker claiming."""
    document = await document_repo.get_document_by_id(db, workspace_id, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Document '{document_id}' not found in workspace '{workspace_id}'.",
                "details": {
                    "workspace_id": str(workspace_id),
                    "document_id": str(document_id),
                },
            },
        )

    if document.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "DOCUMENT_NOT_FAILED",
                "message": f"Document '{document_id}' is in status '{document.status}'. Only failed documents can be retried.",
                "details": {"current_status": document.status},
            },
        )

    # Atomic conditional claim
    claimed = await document_repo.atomic_claim_worker(db, workspace_id, document_id)
    if not claimed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "CONCURRENT_JOB_CLAIM",
                "message": "Document was already claimed for processing by another worker.",
                "details": {"document_id": str(document_id)},
            },
        )

    return claimed
