from truthexpiry.models.claim import ClaimKey, NormalizedScope


def normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def build_claim_key(
    entity: str,
    attribute: str,
    scope: dict[str, str] | None = None,
) -> ClaimKey:
    normalized_scope: dict[str, str] = {}
    for key, value in sorted((scope or {}).items()):
        if not value:
            continue
        normalized_scope[normalize_token(key)] = normalize_token(value)

    return ClaimKey(
        entity=normalize_token(entity),
        attribute=normalize_token(attribute),
        scope=NormalizedScope(fields=normalized_scope),
    )


def parse_canonical_key(canonical: str) -> ClaimKey:
    """Parse a canonical claim key string.

    Test-helper utility for round-tripping keys produced by ``build_claim_key``.
    Unlike ``build_claim_key``, this does not normalize entity or scope tokens.
    """
    parts = canonical.split("|")
    if len(parts) < 2:
        raise ValueError(f"Invalid claim key: {canonical!r}")

    entity, attribute = parts[0], parts[1]
    scope_fields: dict[str, str] = {}
    for fragment in parts[2:]:
        if "=" not in fragment:
            raise ValueError(f"Invalid scope fragment: {fragment!r}")
        key, value = fragment.split("=", 1)
        scope_fields[key] = value

    return ClaimKey(
        entity=entity,
        attribute=attribute,
        scope=NormalizedScope(fields=scope_fields),
    )
