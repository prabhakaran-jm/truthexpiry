from dataclasses import dataclass, field


@dataclass(frozen=True)
class NormalizedScope:
    fields: dict[str, str] = field(default_factory=dict)

    def canonical_fragment(self) -> str:
        return "|".join(f"{key}={value}" for key, value in sorted(self.fields.items()))

    def is_complete(self, required_fields: tuple[str, ...] = ()) -> bool:
        if not required_fields:
            return True
        return all(
            field_name in self.fields and self.fields[field_name]
            for field_name in required_fields
        )


@dataclass(frozen=True)
class ClaimKey:
    entity: str
    attribute: str
    scope: NormalizedScope

    def canonical(self) -> str:
        scope_part = self.scope.canonical_fragment()
        if scope_part:
            return f"{self.entity}|{self.attribute}|{scope_part}"
        return f"{self.entity}|{self.attribute}"


@dataclass(frozen=True)
class EvidenceRef:
    ref_type: str
    value: str
    channel_id: str | None = None
    message_ts: str | None = None


@dataclass(frozen=True)
class ExtractedClaim:
    key: ClaimKey
    stated_value: str
    evidence_refs: tuple[EvidenceRef, ...] = ()
    required_scope_fields: tuple[str, ...] = ()
