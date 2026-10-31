"""Interfaz mínima independiente de SDKs y de la validación de negocio."""

from typing import Protocol


class Provider(Protocol):
    def generate(self, instructions: str, query: str) -> str:
        """Recibir instrucciones y consulta; devolver texto sin validar."""
        ...
