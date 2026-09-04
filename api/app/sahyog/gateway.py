"""SAHYOG gateway — talks to the inter-agency portal."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.sahyog.models import SahyogCase, SahyogMessage, SahyogReceipt


class SahyogGateway(ABC):
    """Outbound gateway to the SAHYOG inter-agency network."""

    @abstractmethod
    async def fetch_case(self, external_id: str) -> SahyogCase:
        """Pull an inbound case from SAHYOG."""
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, message: SahyogMessage) -> SahyogReceipt:
        """Dispatch a message to SAHYOG and return its acknowledgement."""
        raise NotImplementedError


class StubSahyogGateway(SahyogGateway):
    """Stub gateway that records calls in a list."""

    def __init__(self) -> None:
        self.sent: list[SahyogMessage] = []
        self.received: list[SahyogCase] = []

    async def fetch_case(self, external_id: str) -> SahyogCase:
        from uuid import uuid4

        case = SahyogCase(
            id=uuid4(),
            case_number=external_id,
            title=f"Ingested from SAHYOG: {external_id}",
        )
        self.received.append(case)
        return case

    async def send_message(self, message: SahyogMessage) -> SahyogReceipt:
        self.sent.append(message)
        return SahyogReceipt(message_id=message.id, accepted=True, detail="stubbed")


__all__ = ["SahyogGateway", "StubSahyogGateway"]
