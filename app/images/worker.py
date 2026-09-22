"""Bounded in-process worker, backed by durable tasks and atomic database claims."""
import asyncio
import logging
from sqlalchemy.orm import sessionmaker
from app.images.models import ImageArtifact
from app.images.service import image_storage, process_image, reconcile_images

logger = logging.getLogger("trident.images")


def work_once(factory, provider, storage):
    with factory() as db:
        reconcile_images(db)
        item = db.query(ImageArtifact.id).filter_by(status="queued").order_by(ImageArtifact.created_at, ImageArtifact.id).first()
        if item: process_image(db, item.id, provider, storage)


async def image_worker(engine, config, provider, stop):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    while not stop.is_set():
        try:
            await asyncio.to_thread(work_once, factory, provider, image_storage(config))
        except Exception:
            logger.warning("image_worker_iteration_failed")  # no prompt, key or provider payload
        try: await asyncio.wait_for(stop.wait(), timeout=2)
        except asyncio.TimeoutError: pass
