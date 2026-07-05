import uuid
from dataclasses import dataclass
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project
from app.sitewise.gate import overlay_status


@dataclass(frozen=True, slots=True)
class ProjectSeed:
    slug: str
    title: str
    workspace_path: str
    phase: str
    archetype: str
    user_role: str
    state: str
    status: str
    metadata: dict[str, str]


DEFAULT_SITEWISE_PROJECT = ProjectSeed(
    slug="procurement-blockb",
    title="Block B Procurement",
    workspace_path="data/procurement-blockb",
    phase="procurement",
    archetype="small-commercial",
    user_role="architect-pm",
    state="NSW",
    status="active",
    metadata={
        "source": "sitewise-import",
        "import_note": "Seeded from the Clerk local SiteWise corpus for the first hosted cockpit slice.",
    },
)


def slug_from_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower())
    return slug.strip("-") or "project"


async def unique_project_slug(
    session: AsyncSession,
    user_id: uuid.UUID,
    requested_slug: str,
) -> str:
    base_slug = slug_from_title(requested_slug)
    slug = base_slug
    suffix = 2
    while await _project_slug_exists(session, user_id, slug):
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


async def create_project(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    slug: str | None,
    archetype: str | None,
    user_role: str | None,
    state: str | None,
    phase: str,
    building_class: str | None = None,
    work_type: str | None = None,
    taxonomy: dict | None = None,
) -> Project:
    project_slug = await unique_project_slug(session, user_id, slug or title)
    project_metadata = {
        "source": "hosted-create-project",
        "workspace_model": "sitewise-template-v1",
    }
    if taxonomy is not None:
        project_metadata["taxonomy"] = taxonomy
    project = Project(
        owner_user_id=user_id,
        slug=project_slug,
        title=title,
        workspace_path=f"04-projects/{project_slug}",
        phase=phase,
        archetype=archetype,
        building_class=building_class,
        work_type=work_type,
        user_role=user_role,
        state=state,
        status="active",
        project_metadata=project_metadata,
    )
    session.add(project)
    await session.flush()
    await session.refresh(project)
    return project


async def ensure_default_project_catalog(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> None:
    result = await session.execute(
        select(Project.id).where(Project.owner_user_id == user_id).limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return

    seed = DEFAULT_SITEWISE_PROJECT
    session.add(
        Project(
            owner_user_id=user_id,
            slug=seed.slug,
            title=seed.title,
            workspace_path=seed.workspace_path,
            phase=seed.phase,
            archetype=seed.archetype,
            user_role=seed.user_role,
            state=seed.state,
            status=seed.status,
            project_metadata=seed.metadata,
        )
    )
    await session.flush()


async def list_projects(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[Project]:
    result = await session.execute(
        select(Project)
        .where(Project.owner_user_id == user_id)
        .order_by(Project.updated_at.desc(), Project.title.asc())
    )
    return list(result.scalars().all())


async def get_project(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> Project | None:
    return await session.get(Project, project_id)


def user_owns_project(project: Project | None, user_id: uuid.UUID) -> bool:
    return project is not None and project.owner_user_id == user_id


def project_overlay_summary(project: Project) -> dict:
    return overlay_status(
        archetype=project.archetype,
        user_role=project.user_role,
        state=project.state,
    ).model_dump()


async def _project_slug_exists(
    session: AsyncSession,
    user_id: uuid.UUID,
    slug: str,
) -> bool:
    result = await session.execute(
        select(Project.id)
        .where(Project.owner_user_id == user_id, Project.slug == slug)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
