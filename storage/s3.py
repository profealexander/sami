"""
s3.py — Almacenamiento en Amazon S3 (o compatible).
Activo solo cuando STORAGE_BACKEND=s3 en .env.
"""

from config.logger import get_logger
from storage.base import StorageProvider
from config.server import server_config

logger = get_logger("storage.s3")


class S3StorageProvider(StorageProvider):
    """Guarda imágenes en S3 / Backblaze B2 / MinIO."""

    @property
    def nombre(self) -> str:
        return "s3"

    def guardar(self, imagen_bytes: bytes, nombre_archivo: str) -> str:
        import boto3
        from botocore.config import Config

        cfg = server_config
        client_kwargs = {
            "aws_access_key_id": cfg.s3_access_key,
            "aws_secret_access_key": cfg.s3_secret_key,
            "region_name": cfg.s3_region,
        }
        if cfg.s3_endpoint:
            client_kwargs["endpoint_url"] = cfg.s3_endpoint

        s3 = boto3.client("s3", config=Config(retries={"max_attempts": 3}), **client_kwargs)
        key = f"comprobantes/{nombre_archivo}"
        s3.put_object(
            Bucket=cfg.s3_bucket,
            Key=key,
            Body=imagen_bytes,
            ContentType=f"image/{nombre_archivo.split('.')[-1]}",
        )
        url = f"https://{cfg.s3_bucket}.s3.{cfg.s3_region}.amazonaws.com/{key}"
        logger.info("Imagen subida a S3: %s", url)
        return url
