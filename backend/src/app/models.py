"""Pydantic models mirroring shared/ticket.schema.json.

Change these only together with the schema and a row in docs/decisions.md.
tests/test_contract.py fails if the two drift apart.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Category(str, Enum):
    housekeeping = "housekeeping"
    food = "food"
    tech = "tech"
    urgent_clinical = "urgent_clinical"
    unclear = "unclear"


class Department(str, Enum):
    housekeeping = "housekeeping"
    food = "food"
    unit_clerk_it = "unit_clerk_it"
    nurse = "nurse"


class Priority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"


class Status(str, Enum):
    new = "new"
    acknowledged = "acknowledged"
    done = "done"


class Source(str, Enum):
    text = "text"
    quick_button = "quick_button"
    voice = "voice"


CATEGORY_TO_DEPARTMENT: dict[Category, Department] = {
    Category.housekeeping: Department.housekeeping,
    Category.food: Department.food,
    Category.tech: Department.unit_clerk_it,
    Category.urgent_clinical: Department.nurse,
    Category.unclear: Department.nurse,
}


class PatientRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room: str = Field(min_length=1, max_length=20, examples=["412B"])
    text: str = Field(min_length=1, max_length=1000, examples=["Can I get an extra pillow?"])
    language: str | None = Field(default=None, examples=["en"])
    source: Source = Source.text


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str
    category: Category
    department: Department
    priority: Priority
    confidence: float = Field(ge=0, le=1)
    escalate_to_nurse: bool
    reason: str = Field(max_length=300)


class Ticket(Classification):
    ticket_id: str
    room: str
    raw_text: str = Field(min_length=1, max_length=1000)
    status: Status = Status.new
    created_at: datetime
    updated_at: datetime | None = None


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status


def nurse_fallback(language: str = "en", reason: str = "classifier unavailable") -> Classification:
    """Safety rule: when in doubt, route to the nurse as high priority."""
    return Classification(
        language=language,
        category=Category.unclear,
        department=Department.nurse,
        priority=Priority.high,
        confidence=0.0,
        escalate_to_nurse=True,
        reason=reason,
    )
