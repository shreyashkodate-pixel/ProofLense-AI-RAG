"""ProofLens AI — Storage Abstraction Base Interface.

Defines the contract for persisting, reading, and deleting raw PDF documents
across local filesystem and cloud object storage providers.
"""

from abc import ABC, abstractmethod


class BaseStorageService(ABC):
    """Abstract storage service interface."""

    @abstractmethod
    async def save_file(self, relative_path: str, content: bytes) -> str:
        """Save file bytes to the storage backend under relative_path.

        Returns the resolved relative storage path.
        """
        pass

    @abstractmethod
    async def get_file(self, relative_path: str) -> bytes:
        """Read and return file bytes from the given relative path."""
        pass

    @abstractmethod
    async def delete_file(self, relative_path: str) -> bool:
        """Delete file at the given relative path.

        Returns True if deleted or file didn't exist, False on unhandled failure.
        """
        pass

    @abstractmethod
    async def file_exists(self, relative_path: str) -> bool:
        """Check if file exists at the given relative path."""
        pass
