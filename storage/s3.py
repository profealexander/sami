"""
s3.py — Almacenamiento en Amazon S3 (o compatible).
Activo solo cuando STORAGE_BACKEND=s3 en .env.
"""

import os
import tempfile

from config.logger import get_logger
from storage.base import StorageProvider
from config.server import server_config
from utils.exceptions import StorageError

logger = get_logger("storage.s3")

# Singleton para cliente S3 (reutiliza conexión HTTP)
_s3_client = None
_s3_config_hash = None


def _obtener_cliente_s3(cfg):
    """Retorna cliente S3 singleton, creándolo solo si cambia la configuración."""
    global _s3_client, _s3_config_hash
    import boto3
    from botocore.config import Config

    config_hash = hash((cfg.s3_access_key, cfg.s3_region, cfg.s3_endpoint))
    if _s3_client is None or _s3_config_hash != config_hash:
        client_kwargs = {
            "aws_access_key_id": cfg.s3_access_key,
            "aws_secret_access_key": cfg.s3_secret_key,
            "region_name": cfg.s3_region,
        }
        if cfg.s3_endpoint:
            client_kwargs["endpoint_url"] = cfg.s3_endpoint
        _s3_client = boto3.client("s3", config=Config(retries={"max_attempts": 3}), **client_kwargs)
        _s3_config_hash = config_hash
    return _s3_client


class S3StorageProvider(StorageProvider):
    """Guarda imágenes en S3 / Backblaze B2 / MinIO."""

    @property
    def nombre(self) -> str:
        """Nombre del backend: s3."""
        return "s3"

    def guardar(self, imagen_bytes: bytes, nombre_archivo: str) -> str:
        """Sube la imagen a S3 y retorna la URL publica o key del objeto."""
        cfg = server_config
        try:
            s3 = _obtener_cliente_s3(cfg)
            key = f"comprobantes/{nombre_archivo}"
            s3.put_object(
                Bucket=cfg.s3_bucket,
                Key=key,
                Body=imagen_bytes,
                ContentType=f"image/{nombre_archivo.split('.')[-1]}",
            )
            # URL compatible con servicios custom (Backblaze, MinIO)
            if cfg.s3_endpoint:
                url = f"{cfg.s3_endpoint}/{cfg.s3_bucket}/{key}"
            else:
                url = f"https://{cfg.s3_bucket}.s3.{cfg.s3_region}.amazonaws.com/{key}"
            logger.info("Imagen subida a S3: %s", url)
            return url
        except Exception as e:
            raise StorageError(mensaje=f"Error subiendo a S3: {e}", backend="s3") from e

    def resolver_ruta(self, ruta: str) -> str:
        """Descarga imagen de S3 a temporal para OCR."""
        import requests
        logger.info("Descargando imagen remota: %s", ruta)
        resp = requests.get(ruta, timeout=30)
        resp.raise_for_status()
        ext = ruta.split(".")[-1].split("?")[0] if "." in ruta else "jpg"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
        tmp.write(resp.content)
        tmp.close()
        return tmp.name

    def limpiar_temporal(self, ruta: str) -> None:
        """Elimina archivo temporal descargado."""
        if ruta and os.path.exists(ruta):
            os.remove(ruta)
            logger.debug("Temporal eliminado: %s", ruta)
