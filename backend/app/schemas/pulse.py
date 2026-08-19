from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.projects.pulse import PULSE_SIGNAL_TYPES, parse_signal_type


class PulseDismissRequest(BaseModel):
    subject_key: str = Field(min_length=1, max_length=255)

    @field_validator("subject_key")
    @classmethod
    def known_signal_type(cls, value: str) -> str:
        if parse_signal_type(value) is None:
            raise ValueError(
                "subject_key must start with a Pulse signal type: "
                + ", ".join(sorted(PULSE_SIGNAL_TYPES))
            )
        return value
