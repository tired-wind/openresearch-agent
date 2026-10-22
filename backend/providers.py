"""Provider contract only. No endpoint is guessed and no paid provider autoactivates."""
from typing import Protocol
from pydantic import BaseModel, Field

class PlanProposal(BaseModel):
    objectives: list[str] = Field(max_length=8)
    limitations: list[str] = Field(max_length=12)

class ResearchProvider(Protocol):
    def propose(self, question: str, schema: dict) -> PlanProposal: ...

class DisabledProvider:
    def propose(self, question: str, schema: dict) -> PlanProposal:
        raise RuntimeError('No model provider configured or verified. Use the explicitly labeled deterministic workflow.')
