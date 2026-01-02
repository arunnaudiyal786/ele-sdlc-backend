from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel

TRequest = TypeVar("TRequest", bound=BaseModel)
TResponse = TypeVar("TResponse", bound=BaseModel)


class BaseComponent(ABC, Generic[TRequest, TResponse]):
    """Abstract base for all components.

    Each component implements this interface, providing:
    - component_name: Unique identifier for logging/metrics
    - process(): Main async entry point
    - health_check(): Component-level health status
    """

    @property
    @abstractmethod
    def component_name(self) -> str:
        """Unique identifier for this component."""
        pass

    @abstractmethod
    async def process(self, request: TRequest) -> TResponse:
        """Main processing entry point."""
        pass

    async def health_check(self) -> dict:
        """Check component health status."""
        return {"component": self.component_name, "status": "healthy"}

    async def __call__(self, request: TRequest) -> TResponse:
        """Allow component to be called directly."""
        return await self.process(request)
