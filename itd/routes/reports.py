from __future__ import annotations
from uuid import UUID
from typing import TYPE_CHECKING

from itd.enums import ReportTargetReason, ReportTargetType

if TYPE_CHECKING:
    from itd.client import Client

def report(client: Client, id: UUID, type: ReportTargetType = ReportTargetType.POST, reason: ReportTargetReason = ReportTargetReason.OTHER, description: str | None = None):
    if description is None:
        description = ''
    return client.request('post', 'reports', {'targetId': str(id), 'targetType': type.value, 'reason': reason.value, 'description': description})
