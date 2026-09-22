"""Images use the existing session/CSRF and Workspace permission dependencies."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.database.database import get_db
from app.security.authorization import require_workspace_access
from app.tenancy.service import TenantContext
from app.images.models import ImageArtifact
from app.images.contracts import MAX_IMAGE_BYTES, ASPECT_SIZES
from app.images.service import enqueue_image, get_artifact, serialize_artifact, image_storage, change_task
from app.api.contracts import PageParams, page_meta

router = APIRouter(prefix="/v1/workspaces/{workspace_id}", tags=["Nova images"])


@router.get("/images/capability")
def capability(request: Request, tenant: TenantContext = Depends(require_workspace_access)):
    config = request.app.state.runtime_settings
    available = config.image_provider == "openai" and bool(config.openai_key())
    return {"data": {"available": available, "reason": None if available else "configuration_required", "aspect_ratios": list(ASPECT_SIZES), "max_upload_bytes": MAX_IMAGE_BYTES}, "meta": {}}


@router.post("/conversations/{conversation_id}/images", status_code=202)
async def create_image(conversation_id: str, request: Request,
    prompt: str = Form(min_length=1, max_length=4000), aspect_ratio: str = Form(default="1:1"),
    request_key: str = Form(min_length=1, max_length=64), source_id: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    db: Session = Depends(get_db), tenant: TenantContext = Depends(require_workspace_access)):
    source = await image.read(MAX_IMAGE_BYTES + 1) if image else None
    item = await run_in_threadpool(enqueue_image, db, tenant, conversation_id, prompt, aspect_ratio, request_key, request.app.state.runtime_settings, source_id=source_id, source=source)
    return {"data": serialize_artifact(item, tenant.principal.user_id), "meta": {}}


@router.get("/images")
def list_images(conversation_id: str | None = None, page: PageParams = Depends(), db: Session = Depends(get_db), tenant: TenantContext = Depends(require_workspace_access)):
    query = db.query(ImageArtifact).filter_by(workspace_id=tenant.workspace_id)
    if conversation_id: query = query.filter_by(conversation_id=conversation_id)
    total = query.count()
    items = query.order_by(ImageArtifact.created_at.desc(), ImageArtifact.id.desc()).offset(page.offset).limit(page.limit).all()
    return {"data": [serialize_artifact(item, tenant.principal.user_id) for item in items], "meta": {"pagination": page_meta(page, total)}}


@router.get("/images/{artifact_id}/content")
def image_content(artifact_id: str, request: Request, db: Session = Depends(get_db), tenant: TenantContext = Depends(require_workspace_access)):
    item = get_artifact(db, tenant.workspace_id, artifact_id)
    if item.status != "completed" or not item.output_key: raise HTTPException(409, "Image non disponible.")
    try: content = image_storage(request.app.state.runtime_settings).read(item.output_key)
    except OSError: raise HTTPException(404, "Image indisponible.") from None
    return Response(content, media_type="image/png", headers={"Cache-Control": "private, no-store", "Content-Disposition": f'inline; filename="nova-{item.id}.png"', "X-Content-Type-Options": "nosniff"})


@router.post("/images/{artifact_id}/retry")
def retry(artifact_id: str, request: Request, db: Session = Depends(get_db), tenant: TenantContext = Depends(require_workspace_access)):
    return {"data": serialize_artifact(change_task(db, tenant, artifact_id, "retry", request.app.state.runtime_settings), tenant.principal.user_id)}


@router.post("/images/{artifact_id}/cancel")
def cancel(artifact_id: str, request: Request, db: Session = Depends(get_db), tenant: TenantContext = Depends(require_workspace_access)):
    return {"data": serialize_artifact(change_task(db, tenant, artifact_id, "cancel", request.app.state.runtime_settings), tenant.principal.user_id)}
