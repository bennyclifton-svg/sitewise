from types import SimpleNamespace
import asyncio
import uuid

from scripts.audit_evidence_identity import audit_evidence_identity


def run_async(coro):
    return asyncio.run(coro)


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Session:
    def __init__(self, rows):
        self.rows = rows
        self.info = {}
        self.execute_count = 0

    async def execute(self, _statement):
        self.execute_count += 1
        return _Result(self.rows)


def _row(path, *, project_id=None, owners=(), platform=False):
    return SimpleNamespace(
        id=uuid.uuid4(),
        relative_path=path,
        project_id=project_id,
        source_type="reference" if platform else "project_evidence",
        document_metadata={"knowledge_scope": "platform"} if platform else {},
        owner_count=len(owners),
        owner_ids=list(owners),
    )


def test_audit_reports_same_path_and_ambiguous_ownership_without_writes() -> None:
    first = uuid.uuid4()
    second = uuid.uuid4()
    session = _Session(
        [
            _row("04-projects/shared/report.pdf", project_id=first, owners=(first, second)),
            _row("04-projects/shared/report.pdf", project_id=second, owners=(second,)),
            _row("sitewise-platform/doctrine.md", platform=True),
        ]
    )

    result = run_async(audit_evidence_identity(session))

    assert result.ambiguous_owner_rows == 1
    assert result.cross_project_duplicate_paths == 1
    assert result.platform_rows == 1
    assert result.identifiers == []
    assert session.execute_count == 1


def test_audit_identifiers_are_explicit_opt_in() -> None:
    owners = (uuid.uuid4(), uuid.uuid4())
    result = run_async(
        audit_evidence_identity(
            _Session([_row("same/path.pdf", owners=owners)]), show_identifiers=True
        )
    )
    assert result.identifiers[0]["relative_path"] == "same/path.pdf"


def test_audit_reports_assigned_owner_mismatch_and_within_project_duplicates() -> None:
    assigned = uuid.uuid4()
    linked = uuid.uuid4()
    result = run_async(
        audit_evidence_identity(
            _Session(
                [
                    _row("same/path.pdf", project_id=assigned, owners=(linked,)),
                    _row("same/path.pdf", project_id=linked, owners=(linked,)),
                ]
            )
        )
    )

    assert result.ambiguous_owner_rows == 1
    assert result.assigned_owner_mismatch_rows == 1
    assert result.within_project_duplicate_paths == 1


def test_audit_sql_is_compatible_with_pre_expand_schema() -> None:
    from scripts.audit_evidence_identity import _AUDIT_SQL

    sql = str(_AUDIT_SQL)
    assert "to_jsonb(document)->>'project_id'" in sql
    assert "document.project_id" not in sql
