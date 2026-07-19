# Evidence UUID tenancy rollout and rollback

This runbook covers migrations 021–023. Never use an application database for
tests. Capture command output and aggregate audit counts in the release record;
do not publish document paths or customer content.

## Preconditions and backup

1. Confirm the deployed application is UUID dual-write capable.
2. Take and verify a restorable database backup, including `source_documents`,
   `document_chunks`, `workspace_files`, `message_citations`, and chat tables.
3. Record the application version, database host, current Alembic revision, row
   counts, and backup identifier.
4. Run the read-only audit without `--show-identifiers`. Stop on ambiguous rows
   until the ownership decision is reviewed.

## Expand, migrate, contract

1. Upgrade only to `021_source_document_uuid_expand`.
2. Deploy the dual-write application and verify new project evidence receives a
   project UUID while platform knowledge remains projectless.
3. Run `python scripts/audit_evidence_identity.py` and archive aggregate output.
4. Run `python scripts/repair_evidence_identity.py --dry-run`. Review counts.
5. Run `python scripts/repair_evidence_identity.py --apply` in a change window.
   Re-run it to verify idempotence, then re-run the audit. The unresolved
   ambiguous count must be zero.
6. Upgrade to `022_source_doc_uuid_contract`, then to
   `023_agent_turns`.
7. Verify two owners with the same slug and relative path through evidence API,
   legacy chat, MCP reads, Project Plan, and Cost Plan. Verify historical
   citations still resolve for the owning project.

The repair never deletes or quarantines evidence. It retains the original
document for one owner, creates deterministic project-scoped copies for other
owners, copies chunks, and repoints owning workspace files and citations.

## Rollback

- Before 022: roll the application back only to a version that tolerates the
  nullable `project_id` column; downgrade 021 after confirming no dependency on
  project-scoped IDs.
- Downgrade 022 to remove only the contract checks while retaining the expanded
  UUID schema and project-scoped uniqueness. This remains safe after repair.
- Downgrade 021 only while no cross-project duplicate paths exist. Migration
  021 intentionally refuses to restore global path uniqueness after repair;
  in that state, redeploy the last UUID-aware application or restore the
  verified pre-rollout backup as a coordinated database/application rollback.
- Migration 023 can be downgraded only after agent traffic is stopped. Doing so
  removes durable turn/revocation history and therefore requires disabling all
  agent mutations first.

After rollback, repeat row-count, citation, two-owner isolation, and platform
scope checks. Record the operator, timestamps, backup/restore evidence, and the
exact application and migration revisions.
