from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, List, Literal, Optional
import uuid
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.entities import ToolMemoryModel

MemoryCategory = Literal[
    "SCHEMA_QUIRK",
    "CONTEXTUAL_LOGIC",
    "WORKFLOW_DEPENDENCY",
    "ERROR_RECOVERY",
]


class ToolPlaybookEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str
    tool_name: str
    category: str  # SCHEMA_QUIRK, CONTEXTUAL_LOGIC, WORKFLOW_DEPENDENCY, ERROR_RECOVERY
    pattern_trigger: str
    learned_rule: str
    evidence: Optional[str] = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    observation_count: int = 1
    execution_id: Optional[str] = None
    failure_id: Optional[str] = None
    reflection_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def memory_id(self) -> str:
        return self.id

    def canonical_dict(self) -> dict[str, Any]:
        """Returns a deterministic dictionary representation."""
        return {
            "category": self.category,
            "confidence": round(self.confidence, 4),
            "created_at": self.created_at,
            "evidence": self.evidence,
            "execution_id": self.execution_id,
            "experiment_id": self.experiment_id,
            "failure_id": self.failure_id,
            "id": self.id,
            "learned_rule": self.learned_rule,
            "observation_count": self.observation_count,
            "pattern_trigger": self.pattern_trigger,
            "reflection_id": self.reflection_id,
            "tool_name": self.tool_name,
            "updated_at": self.updated_at,
        }

    def to_canonical_json(self) -> str:
        """Deterministic serialization with sorted keys."""
        return json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":"))


class ToolMemoryStore:
    """
    Persistent in-memory, file-backed, and SQLite database store for tool playbooks and operational heuristics.
    Enables agents to learn, persist, and reuse API quirks, schema rules, and contextual domain logic across runs.
    """

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self._entries: list[ToolPlaybookEntry] = []

    def get_entries(self, tool_names: Optional[list[str]] = None) -> list[ToolPlaybookEntry]:
        """Returns entries filtered by tool names, deterministically sorted by confidence and tool/pattern."""
        if not tool_names:
            return sorted(self._entries, key=lambda e: (-e.confidence, e.tool_name, e.pattern_trigger))
        tools_set = set(tool_names)
        matched = [e for e in self._entries if e.tool_name in tools_set]
        return sorted(matched, key=lambda e: (-e.confidence, e.tool_name, e.pattern_trigger))

    def retrieve_playbooks(
        self,
        tool_names: Optional[list[str]] = None,
        category: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> list[ToolPlaybookEntry]:
        """Retrieve relevant playbooks with optional category and confidence threshold filtering."""
        entries = self.get_entries(tool_names)
        if category:
            entries = [e for e in entries if e.category == category]
        if min_confidence > 0.0:
            entries = [e for e in entries if e.confidence >= min_confidence]
        return sorted(entries, key=lambda e: (-e.confidence, e.tool_name, e.pattern_trigger))

    def save_playbook(
        self,
        tool_name: str,
        category: str,
        pattern_trigger: str,
        learned_rule: str,
        evidence: Optional[str] = None,
        confidence: float = 0.85,
        execution_id: Optional[str] = None,
        failure_id: Optional[str] = None,
        reflection_id: Optional[str] = None,
    ) -> ToolPlaybookEntry:
        """Explicit save interface matching memory contract."""
        return self.add_or_update(
            tool_name=tool_name,
            category=category,
            pattern_trigger=pattern_trigger,
            learned_rule=learned_rule,
            evidence=evidence,
            confidence=confidence,
            execution_id=execution_id,
            failure_id=failure_id,
            reflection_id=reflection_id,
        )

    def save_reflected_rule(self, rule: Any) -> ToolPlaybookEntry:
        """Saves a validated ReflectedRule into persistent memory."""
        return self.save_playbook(
            tool_name=getattr(rule, "tool_name"),
            category=getattr(rule, "category"),
            pattern_trigger=getattr(rule, "pattern_trigger"),
            learned_rule=getattr(rule, "learned_rule"),
            evidence=getattr(rule, "evidence", None),
            confidence=getattr(rule, "confidence", 0.85),
            execution_id=getattr(rule, "execution_id", None),
            failure_id=getattr(rule, "failure_id", None),
            reflection_id=getattr(rule, "id", None) or getattr(rule, "reflection_id", None),
        )

    def add_or_update(
        self,
        tool_name: str,
        category: str,
        pattern_trigger: str,
        learned_rule: str,
        evidence: Optional[str] = None,
        confidence: float = 0.85,
        execution_id: Optional[str] = None,
        failure_id: Optional[str] = None,
        reflection_id: Optional[str] = None,
    ) -> ToolPlaybookEntry:
        valid_categories = ("SCHEMA_QUIRK", "CONTEXTUAL_LOGIC", "WORKFLOW_DEPENDENCY", "ERROR_RECOVERY")
        if category not in valid_categories:
            raise ValueError(
                f"Invalid memory category '{category}'. Only validated categories {valid_categories} can be persisted."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        clamped_conf = round(max(0.0, min(1.0, confidence)), 3)

        # Check if an existing entry shares the same tool and pattern trigger (deterministic deduplication)
        for entry in self._entries:
            if entry.tool_name == tool_name and (
                entry.pattern_trigger.lower() in pattern_trigger.lower()
                or pattern_trigger.lower() in entry.pattern_trigger.lower()
            ):
                entry.observation_count += 1
                # Deterministic arithmetic confidence update (+0.05 per observation, clamped to 1.0)
                entry.confidence = round(min(1.0, entry.confidence + 0.05), 3)
                entry.learned_rule = learned_rule  # update with latest refined rule
                entry.updated_at = now_iso
                # Preserve original evidence reference from the first discovery
                if not entry.evidence and evidence:
                    entry.evidence = evidence
                if execution_id and not entry.execution_id:
                    entry.execution_id = execution_id
                if failure_id and not entry.failure_id:
                    entry.failure_id = failure_id
                if reflection_id and not entry.reflection_id:
                    entry.reflection_id = reflection_id
                return entry

        new_entry = ToolPlaybookEntry(
            experiment_id=self.experiment_id,
            tool_name=tool_name,
            category=category,
            pattern_trigger=pattern_trigger,
            learned_rule=learned_rule,
            evidence=evidence,
            confidence=clamped_conf,
            observation_count=1,
            execution_id=execution_id,
            failure_id=failure_id,
            reflection_id=reflection_id,
            created_at=now_iso,
            updated_at=now_iso,
        )
        self._entries.append(new_entry)
        return new_entry

    def format_for_prompt(self, tool_names: Optional[list[str]] = None) -> str:
        """Formats the learned tool playbooks into a concise, high-priority system prompt injection.
        Returns empty string when no relevant playbooks exist."""
        entries = self.retrieve_playbooks(tool_names=tool_names)
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

    def to_canonical_json(self) -> str:
        """Deterministic serialization of entire store sorted by canonical keys."""
        sorted_entries = [e.canonical_dict() for e in self.get_entries()]
        return json.dumps(sorted_entries, sort_keys=True, separators=(",", ":"))

    def save_to_file(self, path: Path | str) -> None:
        """Persists memory store to a local JSON file."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_canonical_json(), encoding="utf-8")

    def load_from_file(self, path: Path | str) -> None:
        """Loads memory playbooks from a local JSON file."""
        target = Path(path)
        if not target.exists():
            return
        raw = json.loads(target.read_text(encoding="utf-8"))
        self._entries = [ToolPlaybookEntry(**item) for item in raw]

    async def sync_from_db(self, db: AsyncSession):
        stmt = (
            select(ToolMemoryModel)
            .where(ToolMemoryModel.experiment_id == self.experiment_id)
            .order_by(ToolMemoryModel.created_at.asc(), ToolMemoryModel.id.asc())
        )
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
                execution_id=m.execution_id,
                failure_id=m.failure_id,
                reflection_id=m.reflection_id,
                created_at=m.created_at.isoformat() if m.created_at else datetime.now(timezone.utc).isoformat(),
                updated_at=m.updated_at.isoformat() if m.updated_at else datetime.now(timezone.utc).isoformat(),
            )
            for m in models
        ]

    async def sync_to_db(self, db: AsyncSession):
        now = datetime.now(timezone.utc)
        for entry in self._entries:
            stmt = select(ToolMemoryModel).where(ToolMemoryModel.id == entry.id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                existing.confidence = entry.confidence
                existing.observation_count = entry.observation_count
                existing.learned_rule = entry.learned_rule
                existing.evidence = entry.evidence
                if entry.execution_id and not existing.execution_id:
                    existing.execution_id = entry.execution_id
                if entry.failure_id and not existing.failure_id:
                    existing.failure_id = entry.failure_id
                if entry.reflection_id and not existing.reflection_id:
                    existing.reflection_id = entry.reflection_id
                existing.updated_at = now
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
                    execution_id=entry.execution_id,
                    failure_id=entry.failure_id,
                    reflection_id=entry.reflection_id,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_model)
        await db.commit()
