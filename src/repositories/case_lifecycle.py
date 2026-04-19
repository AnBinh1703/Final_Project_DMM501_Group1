from __future__ import annotations

VALID_CASE_STATUSES = {
    "NEW",
    "QUEUED",
    "IN_REVIEW",
    "ESCALATED",
    "CONFIRMED_FRAUD",
    "FALSE_POSITIVE",
    "BLOCKED",
    "RELEASED",
    "RESOLVED",
}

ACTIVE_REVIEW_STATUSES = {"NEW", "QUEUED", "IN_REVIEW", "ESCALATED"}


def status_to_event(status: str) -> str:
    mapping = {
        "NEW": "CASE_ASSIGNED",
        "QUEUED": "CASE_ASSIGNED",
        "IN_REVIEW": "INVESTIGATION_STARTED",
        "ESCALATED": "ESCALATED",
        "CONFIRMED_FRAUD": "CONFIRMED_FRAUD",
        "FALSE_POSITIVE": "FALSE_POSITIVE",
        "BLOCKED": "BLOCKED",
        "RELEASED": "RELEASED",
        "RESOLVED": "CASE_CLOSED",
    }
    return mapping.get(status, "STATUS_UPDATED")
