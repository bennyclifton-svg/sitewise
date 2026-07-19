import uuid

from ingest.ids import CHUNK_NAMESPACE, DOC_NAMESPACE, chunk_id, document_id


def test_project_document_ids_are_stable_and_project_scoped() -> None:
    path = "04-projects/shared/_inbox/quote.pdf"
    first_project = uuid.UUID("11111111-1111-1111-1111-111111111111")
    second_project = uuid.UUID("22222222-2222-2222-2222-222222222222")

    first = document_id(path, project_id=first_project)

    assert first == document_id(path, project_id=first_project)
    assert first != document_id(path, project_id=second_project)


def test_platform_document_ids_retain_the_historical_recipe() -> None:
    path = "seed/cost-management-principles.md"

    assert document_id(path) == uuid.uuid5(DOC_NAMESPACE, path)


def test_new_chunk_ids_are_scoped_to_the_persisted_document() -> None:
    first_document = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    second_document = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    assert chunk_id(first_document, 0) == uuid.uuid5(
        CHUNK_NAMESPACE, f"{first_document}:0"
    )
    assert chunk_id(first_document, 0) != chunk_id(second_document, 0)
