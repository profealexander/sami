"""
base.py — Clase abstracta para backends de almacenamiento.

Cada backend debe implementar guardar().
Retorna la ruta (local) o URL (S3/Cloudinary) donde quedó la imagen.
"""

from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """Interfaz que todo backend de almacenamiento debe implementar."""

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Nombre del backend (local, s3, cloudinary)."""
        ...

    @abstractmethod
    def guardar(self, imagen_bytes: bytes, nombre_archivo: str) -> str:
        """
        Guarda una imagen y retorna su ruta o URL accesible.

        Args:
            imagen_bytes: Contenido binario de la imagen
            nombre_archivo: Nombre con extensión (ej: "abc123.jpg")

        Returns:
            str: Ruta local relativa o URL pública
        """
        ...

    def es_local(self) -> bool:
        """Retorna True si el backend almacena en disco local."""
        return False

    def resolver_ruta(self, ruta: str) -> str:
        """Resuelve una ruta de BD a ruta accesible para OCR.

        Para backends locales, retorna la ruta absoluta.
        Para remotos, descarga a temporal y retorna esa ruta.
        """
        return ruta

    def limpiar_temporal(self, ruta: str) -> None:
        """Limpia archivos temporales creados durante resolver_ruta."""
        pass
