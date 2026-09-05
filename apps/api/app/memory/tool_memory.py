from datetime import datetime, timezone
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.entities import ToolMemoryModel


class ToolPlaybookEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str
    tool_name: str
    category: str  # SCHEMA_QUIRK, CONTEXTUAL_LOGIC, WORKFLOW_DEPENDENCY, ERROR_RECOVERY
    pattern_trigger: str
    learned_rule: str
    evidence: Optional[str] = None
    confidence: float = 0.85
    observation_count: int = 1
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ToolMemoryStore:
    """
    Persistent in-memory & database store for tool playbooks and operational heuristics.
    Enables agents to learn and reuse API quirks, schema rules, and contextual domain logic across runs.
    """

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self._entries: list[ToolPlaybookEntry] = []

    def get_entries(self, tool_names: Optional[list[str]] = None) -> list[ToolPlaybookEntry]:
        if not tool_names:
            return list(self._entries)
        tools_set = set(tool_names)
        return [e for e in self._entries if e.tool_name in tools_set]

    def add_or_update(
        self,
        tool_name: str,
        category: str,
        pattern_trigger: str,
        learned_rule: str,
        evidence: Optional[str] = None,
        confidence: float = 0.85,
    ) -> ToolPlaybookEntry:
        # Check if an existing entry shares the same tool and pattern
        for entry in self._entries:
            if entry.tool_name == tool_name and (
                entry.pattern_trigger.lower() in pattern_trigger.lower()
                or pattern_trigger.lower() in entry.pattern_trigger.lower()
            ):
                entry.observation_count += 1
                entry.confidence = round(min(1.0, entry.confidence + 0.05), 3)
                entry.learned_rule = learned_rule  # update with latest refined rule
                if evidence:
                    entry.evidence = evidence
                return entry

        new_entry = ToolPlaybookEntry(
            experiment_id=self.experiment_id,
            tool_name=tool_name,
            category=category,
            pattern_trigger=pattern_trigger,
            learned_rule=learned_rule,
            evidence=evidence,
            confidence=confidence,
            observation_count=1,
        )
        self._entries.append(new_entry)
        return new_entry

    def format_for_prompt(self, tool_names: Optional[list[str]] = None) -> str:
        """Formats the learned tool playbooks into a concise, high-priority system prompt injection."""
        entries = self.get_entries(tool_names)
        if not entries:
            return ""

        lines = [
            "### [LEARNED TOOL PLAYBOOK & CONTEXTUAL MEMORY]",
            "The following operational rules, API quirks, and domain conventions were learned from prior runs.",
            "Apply them directly to avoid redundant exploratory calls and API errors:\n",
        ]
        for i, e in enumerate(entries, 1):
            lines.append(f"{i}. [{e.tool_name.upper()} | {e.category}]")
            lines.append(f"   • When: {e.pattern_trigger}")
            lines.append(f"   • Actionable Rule: {e.learned_rule}")
            if e.evidence:
                short_ev = (e.evidence[:140] + "...") if len(e.evidence) > 140 else e.evidence
                lines.append(f"   • Learned from: {short_ev}")
            lines.append(f"   • Confidence: {e.confidence * 100:.0f}% (observed {e.observation_count}x)\n")

        return "\n".join(lines)

    async def sync_from_db(self, db: AsyncSession):
        stmt = select(ToolMemoryModel).where(ToolMemoryModel.experiment_id == self.experiment_id)
        res = await db.execute(stmt)
        models = res.scalars().all()
        self._entries = [
            ToolPlaybookEntry(
                id=m.id,
                experiment_id=m.experiment_id,
                tool_name=m.tool_name,
                category=m.category,
                pattern_trigger=m.pattern_trigger,
                learned_rule=m.learned_rule,
                evidence=m.evidence,
                confidence=m.confidence,
                observation_count=m.observation_count,
                created_at=m.created_at.isoformat() if m.created_at else datetime.now(timezone.utc).isoformat(),
            )
            for m in models
        ]

    async def sync_to_db(self, db: AsyncSession):
        for entry in self._entries:
            stmt = select(ToolMemoryModel).where(ToolMemoryModel.id == entry.id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                existing.confidence = entry.confidence
                existing.observation_count = entry.observation_count
                existing.learned_rule = entry.learned_rule
                existing.evidence = entry.evidence
            else:
                new_model = ToolMemoryModel(
                    id=entry.id,
                    experiment_id=self.experiment_id,
                    tool_name=entry.tool_name,
                    category=entry.category,
                    pattern_trigger=entry.pattern_trigger,
                    learned_rule=entry.learned_rule,
                    evidence=entry.evidence,
                    confidence=entry.confidence,
                    observation_count=entry.observation_count,
                )
                db.add(new_model)
        await db.commit()
