export type ProgrammeScale = "week" | "month" | "quarter";
export type ProgrammeKind = "stage" | "activity" | "milestone";
export type DependencyEndpoint = "start" | "finish";

export type ProgrammeActivity = {
  activity_key: string;
  kind: ProgrammeKind;
  parent_key: string | null;
  name: string;
  display_order: number;
  start_date: string;
  duration_days: number;
  finish_date: string | null;
  assumption: boolean;
  notes: string;
};

export type ProgrammeState = {
  id: string | null;
  project_id: string;
  version: number;
  status: "proposed" | "accepted" | "superseded";
  view_scale: ProgrammeScale;
  pmp_embed_visible: boolean;
  collapsed_stage_keys: string[];
  activities: ProgrammeActivity[];
  dependencies?: ProgrammeDependency[];
};

export type ProgrammeDependency = {
  dependency_key: string;
  source_activity_key: string;
  target_activity_key: string;
  source_endpoint: DependencyEndpoint;
  target_endpoint: DependencyEndpoint;
  lag_days: number;
};

export type ProgrammeOperation = {
  operation: "ADD" | "UPDATE" | "DELETE" | "MOVE";
  target_type: ProgrammeKind | "dependency";
  target_id?: string;
  values?: Record<string, unknown>;
  reference_id?: string;
  placement?: "before" | "after";
};

export const DEFAULT_PROGRAMME_SCALE: ProgrammeScale = "month";

export const PROGRAMME_HEADINGS = new Set([
  "programme",
  "program",
  "programme of services",
  "programme and staging regime",
]);

export const PROGRAMME_HEADING_RE =
  /^##\s+(Programme(?: of services)?|Programme and staging regime|Program)\s*$/im;

export function programmeRowMove(
  activities: ProgrammeActivity[],
  sourceKey: string,
  overKey: string,
  placement: "before" | "after",
): ProgrammeOperation | null {
  if (sourceKey === overKey) return null;
  const source = activities.find((item) => item.activity_key === sourceKey);
  const over = activities.find((item) => item.activity_key === overKey);
  if (!source || !over) return null;
  if (source.kind === "stage" && over.parent_key === source.activity_key) {
    return null;
  }
  const sourceIndex = activities.findIndex((item) => item.activity_key === sourceKey);
  const overIndex = activities.findIndex((item) => item.activity_key === overKey);
  if (placement === "after" && sourceIndex === overIndex + 1) return null;
  if (placement === "before" && sourceIndex === overIndex - 1) return null;
  return {
    operation: "MOVE",
    target_type: source.kind,
    target_id: sourceKey,
    reference_id: overKey,
    placement,
  };
}

export function programmeBulkDeleteOperations(
  activities: ProgrammeActivity[],
  selectedKeys: Iterable<string>,
): ProgrammeOperation[] {
  const selected = new Set(selectedKeys);
  return activities
    .filter((item) => {
      if (!selected.has(item.activity_key)) return false;
      return !(item.parent_key && selected.has(item.parent_key));
    })
    .map((item) => ({
      operation: "DELETE" as const,
      target_type: item.kind,
      target_id: item.activity_key,
    }));
}

export function coalesceProgrammeOperations(
  operations: ProgrammeOperation[],
): ProgrammeOperation[] {
  const merged: ProgrammeOperation[] = [];
  for (const operation of operations) {
    const last = merged[merged.length - 1];
    if (
      operation.operation === "UPDATE" &&
      last?.operation === "UPDATE" &&
      last.target_type === operation.target_type &&
      last.target_id &&
      last.target_id === operation.target_id
    ) {
      last.values = { ...last.values, ...operation.values };
      continue;
    }
    merged.push({
      ...operation,
      values: operation.values ? { ...operation.values } : undefined,
    });
  }
  return merged;
}

export function applyProgrammeOperationsLocally(
  state: ProgrammeState,
  operations: ProgrammeOperation[],
): ProgrammeState {
  let activities = state.activities;
  let dependencies = state.dependencies ?? [];
  for (let operation of operations) {
    if (operation.target_type === "dependency") {
      dependencies = applyDependencyLocally(dependencies, activities, operation);
      continue;
    }
    if (operation.operation === "UPDATE" && operation.values?.start_date) {
      const adjusted = adjustMoveLagLocally(activities, dependencies, operation);
      dependencies = adjusted.dependencies;
      if (adjusted.linked) {
        const values = { ...operation.values };
        delete values.start_date;
        if (Object.keys(values).length === 0) continue;
        operation = { ...operation, values };
      }
    }
    activities = applyOneLocally(activities, operation);
    if (operation.operation === "DELETE") {
      const keys = new Set(activities.map((item) => item.activity_key));
      dependencies = dependencies.filter(
        (item) => keys.has(item.source_activity_key) && keys.has(item.target_activity_key),
      );
    }
  }
  return {
    ...state,
    activities: rollupStages(scheduleActivities(activities, dependencies)),
    dependencies,
  };
}

function applyOneLocally(
  activities: ProgrammeActivity[],
  operation: ProgrammeOperation,
): ProgrammeActivity[] {
  if (operation.operation === "ADD") {
    return addLocally(activities, operation);
  }
  if (operation.operation === "UPDATE") {
    return updateLocally(activities, operation);
  }
  if (operation.operation === "DELETE") {
    return deleteLocally(activities, operation.target_id);
  }
  if (operation.operation === "MOVE") {
    return moveLocally(activities, operation);
  }
  return activities;
}

function addLocally(
  activities: ProgrammeActivity[],
  operation: ProgrammeOperation,
): ProgrammeActivity[] {
  const values = operation.values ?? {};
  const name = String(values.name ?? "").trim() || "New activity";
  const key = uniqueActivityKey(
    activities,
    String(values.activity_key ?? activitySlug(name)),
  );
  const parentKey =
    operation.target_type === "stage"
      ? null
      : String(values.parent_key ?? "") || null;
  const start =
    typeof values.start_date === "string"
      ? values.start_date
      : activities[0]?.start_date ?? toIsoDate(new Date());
  const duration =
    typeof values.duration_days === "number"
      ? values.duration_days
      : operation.target_type === "milestone"
        ? 0
        : 14;
  const item: ProgrammeActivity = {
    activity_key: key,
    kind: operation.target_type as ProgrammeKind,
    parent_key: parentKey,
    name,
    display_order: activities.length,
    start_date: start,
    duration_days: duration,
    finish_date: operation.target_type === "milestone" ? start : addDays(start, duration),
    assumption: true,
    notes: "",
  };
  if (!operation.reference_id) {
    return treeOrder([...activities, item]);
  }
  const insertAt = insertIndex(activities, operation.reference_id, operation.placement);
  const next = [...activities];
  next.splice(
    item.kind === "stage" && operation.placement !== "before"
      ? afterStageBlock(activities, operation.reference_id, insertAt)
      : insertAt,
    0,
    item,
  );
  return treeOrder(next);
}

function updateLocally(
  activities: ProgrammeActivity[],
  operation: ProgrammeOperation,
): ProgrammeActivity[] {
  const values = operation.values ?? {};
  return activities.map((item) => {
    if (item.activity_key !== operation.target_id) return item;
    const next = { ...item };
    if (typeof values.name === "string" && values.name.trim()) next.name = values.name.trim();
    if (typeof values.duration_days === "number") {
      next.duration_days = Math.max(item.kind === "milestone" ? 0 : 1, values.duration_days);
    }
    if (typeof values.start_date === "string" && values.start_date) {
      next.start_date = values.start_date;
    }
    next.finish_date =
      next.kind === "milestone" ? next.start_date : addDays(next.start_date, next.duration_days);
    return next;
  });
}

function deleteLocally(
  activities: ProgrammeActivity[],
  targetId: string | undefined,
): ProgrammeActivity[] {
  if (!targetId) return activities;
  return treeOrder(
    activities.filter(
      (item) => item.activity_key !== targetId && item.parent_key !== targetId,
    ),
  );
}

function moveLocally(
  activities: ProgrammeActivity[],
  operation: ProgrammeOperation,
): ProgrammeActivity[] {
  const item = activities.find((row) => row.activity_key === operation.target_id);
  const reference = activities.find((row) => row.activity_key === operation.reference_id);
  if (!item || !reference || item.activity_key === reference.activity_key) return activities;
  const placement = operation.placement ?? "after";
  if (item.kind === "stage") {
    const refStage =
      reference.kind === "stage"
        ? reference
        : activities.find((row) => row.activity_key === reference.parent_key);
    if (!refStage || refStage.activity_key === item.activity_key) return activities;
    const blockKeys = new Set([
      item.activity_key,
      ...activities
        .filter((row) => row.parent_key === item.activity_key)
        .map((row) => row.activity_key),
    ]);
    const block = activities.filter((row) => blockKeys.has(row.activity_key));
    const remaining = activities.filter((row) => !blockKeys.has(row.activity_key));
    let insertAt = remaining.findIndex((row) => row.activity_key === refStage.activity_key);
    if (insertAt < 0) return activities;
    if (placement === "after") {
      insertAt = afterStageBlock(remaining, refStage.activity_key, insertAt + 1);
    }
    return treeOrder([...remaining.slice(0, insertAt), ...block, ...remaining.slice(insertAt)]);
  }
  const remaining = activities.filter((row) => row.activity_key !== item.activity_key);
  let parentKey: string | null;
  let insertAt: number;
  if (reference.kind === "stage") {
    if (placement === "after") {
      parentKey = reference.activity_key;
      insertAt = remaining.findIndex((row) => row.activity_key === reference.activity_key) + 1;
    } else {
      const previousStage = remaining
        .slice(
          0,
          remaining.findIndex((row) => row.activity_key === reference.activity_key),
        )
        .findLast((row) => row.kind === "stage");
      if (previousStage) {
        parentKey = previousStage.activity_key;
        insertAt = afterStageBlock(
          remaining,
          previousStage.activity_key,
          remaining.findIndex((row) => row.activity_key === previousStage.activity_key) + 1,
        );
      } else {
        parentKey = reference.activity_key;
        insertAt = remaining.findIndex((row) => row.activity_key === reference.activity_key) + 1;
      }
    }
  } else {
    parentKey = reference.parent_key;
    insertAt = insertIndex(remaining, reference.activity_key, placement);
  }
  return treeOrder([
    ...remaining.slice(0, insertAt),
    { ...item, parent_key: parentKey },
    ...remaining.slice(insertAt),
  ]);
}

export function programmeDependencyKey(
  sourceActivityKey: string,
  sourceEndpoint: DependencyEndpoint,
  targetActivityKey: string,
  targetEndpoint: DependencyEndpoint,
): string {
  return `${sourceActivityKey}:${sourceEndpoint}->${targetActivityKey}:${targetEndpoint}`;
}

function applyDependencyLocally(
  dependencies: ProgrammeDependency[],
  activities: ProgrammeActivity[],
  operation: ProgrammeOperation,
): ProgrammeDependency[] {
  if (operation.operation === "ADD") {
    const values = operation.values ?? {};
    const source_activity_key = String(values.source_activity_key ?? "");
    const target_activity_key = String(values.target_activity_key ?? "");
    const source_endpoint = values.source_endpoint === "start" ? "start" : "finish";
    const target_endpoint = values.target_endpoint === "finish" ? "finish" : "start";
    if (!source_activity_key || !target_activity_key) return dependencies;
    if (
      programmeDependencyWouldCycle(
        activities,
        dependencies,
        source_activity_key,
        target_activity_key,
      )
    ) {
      return dependencies;
    }
    const dependency: ProgrammeDependency = {
      dependency_key: String(
        values.dependency_key ??
          programmeDependencyKey(
            source_activity_key,
            source_endpoint,
            target_activity_key,
            target_endpoint,
          ),
      ),
      source_activity_key,
      target_activity_key,
      source_endpoint,
      target_endpoint,
      lag_days: Math.max(0, Number(values.lag_days ?? 0)),
    };
    return dependencies.some((item) => item.dependency_key === dependency.dependency_key)
      ? dependencies
      : [...dependencies, dependency];
  }
  const targetId = operation.target_id;
  if (!targetId) return dependencies;
  if (operation.operation === "DELETE") {
    return dependencies.filter((item) => item.dependency_key !== targetId);
  }
  if (operation.operation === "UPDATE") {
    return dependencies.map((item) =>
      item.dependency_key === targetId
        ? {
            ...item,
            lag_days:
              typeof operation.values?.lag_days === "number"
                ? Math.max(0, operation.values.lag_days)
                : item.lag_days,
          }
        : item,
    );
  }
  return dependencies;
}

function adjustMoveLagLocally(
  activities: ProgrammeActivity[],
  dependencies: ProgrammeDependency[],
  operation: ProgrammeOperation,
): { dependencies: ProgrammeDependency[]; linked: boolean } {
  const target = activities.find((item) => item.activity_key === operation.target_id);
  const desiredStart = operation.values?.start_date;
  if (!target || typeof desiredStart !== "string") return { dependencies, linked: false };
  const byKey = new Map(activities.map((item) => [item.activity_key, item]));
  const incoming = dependencies
    .filter((item) => item.target_activity_key === target.activity_key)
    .map((item) => {
      const source = byKey.get(item.source_activity_key);
      return source
        ? { item, constraint: dependencyConstraintStart(item, source, target.duration_days) }
        : null;
    })
    .filter((item): item is { item: ProgrammeDependency; constraint: string } => item !== null)
    .sort((left, right) =>
      left.constraint === right.constraint
        ? left.item.dependency_key.localeCompare(right.item.dependency_key)
        : left.constraint.localeCompare(right.constraint),
    );
  const driving = incoming.at(-1)?.item;
  if (!driving) return { dependencies, linked: false };
  const delta = daysBetween(target.start_date, desiredStart);
  return {
    dependencies: dependencies.map((item) =>
      item.dependency_key === driving.dependency_key
        ? { ...item, lag_days: Math.max(0, item.lag_days + delta) }
        : item,
    ),
    linked: true,
  };
}

function dependencyConstraintStart(
  dependency: ProgrammeDependency,
  source: ProgrammeActivity,
  targetDuration: number,
): string {
  const sourceAnchor =
    dependency.source_endpoint === "start"
      ? source.start_date
      : (source.finish_date ?? source.start_date);
  return addDays(
    sourceAnchor,
    dependency.lag_days - (dependency.target_endpoint === "finish" ? targetDuration : 0),
  );
}

function scheduleActivities(
  activities: ProgrammeActivity[],
  dependencies: ProgrammeDependency[],
): ProgrammeActivity[] {
  const byKey = new Map(activities.map((item) => [item.activity_key, item]));
  const incoming = new Map<string, ProgrammeDependency[]>();
  for (const dependency of dependencies) {
    const bucket = incoming.get(dependency.target_activity_key) ?? [];
    bucket.push(dependency);
    incoming.set(dependency.target_activity_key, bucket);
  }
  const resolved = new Map<string, ProgrammeActivity>();
  const visiting = new Set<string>();

  function resolve(key: string): ProgrammeActivity {
    const cached = resolved.get(key);
    if (cached) return cached;
    const row = byKey.get(key);
    if (!row) throw new Error(`activity ${key} was not found`);
    if (visiting.has(key)) throw new Error(`dependency cycle involving ${key}`);
    visiting.add(key);
    let start = row.start_date;
    const constraints = incoming.get(key) ?? [];
    if (constraints.length) {
      start = constraints.reduce((latest, dependency) => {
        const source = resolve(dependency.source_activity_key);
        const candidate = dependencyConstraintStart(dependency, source, row.duration_days);
        return candidate > latest ? candidate : latest;
      }, "0000-00-00");
    }
    const finish = row.kind === "milestone" ? start : addDays(start, row.duration_days);
    const scheduled = { ...row, start_date: start, finish_date: finish };
    visiting.delete(key);
    resolved.set(key, scheduled);
    return scheduled;
  }

  return activities.map((item) => resolve(item.activity_key));
}

function rollupStages(activities: ProgrammeActivity[]): ProgrammeActivity[] {
  const children = new Map<string, ProgrammeActivity[]>();
  for (const item of activities) {
    if (!item.parent_key) continue;
    const bucket = children.get(item.parent_key) ?? [];
    bucket.push(item);
    children.set(item.parent_key, bucket);
  }
  return activities.map((item) => {
    const kids = children.get(item.activity_key);
    if (item.kind !== "stage" || !kids?.length) return item;
    const start = kids.reduce(
      (min, child) => (child.start_date < min ? child.start_date : min),
      kids[0].start_date,
    );
    const finish = kids.reduce((max, child) => {
      const value = child.finish_date || child.start_date;
      return value > max ? value : max;
    }, kids[0].finish_date || kids[0].start_date);
    return {
      ...item,
      start_date: start,
      finish_date: finish,
      duration_days: daysBetween(start, finish),
    };
  });
}

function treeOrder(activities: ProgrammeActivity[]): ProgrammeActivity[] {
  const stages = activities.filter((item) => item.kind === "stage");
  const children = new Map<string, ProgrammeActivity[]>();
  const loose: ProgrammeActivity[] = [];
  for (const item of activities) {
    if (item.kind === "stage") continue;
    if (item.parent_key) {
      const bucket = children.get(item.parent_key) ?? [];
      bucket.push(item);
      children.set(item.parent_key, bucket);
    } else {
      loose.push(item);
    }
  }
  const ordered: ProgrammeActivity[] = [];
  for (const stage of stages) {
    ordered.push(stage);
    ordered.push(...(children.get(stage.activity_key) ?? []));
    children.delete(stage.activity_key);
  }
  for (const leftover of children.values()) ordered.push(...leftover);
  ordered.push(...loose);
  return ordered.map((item, index) =>
    item.display_order === index ? item : { ...item, display_order: index },
  );
}

function insertIndex(
  activities: ProgrammeActivity[],
  referenceId: string,
  placement: "before" | "after" | undefined,
): number {
  const index = activities.findIndex((item) => item.activity_key === referenceId);
  if (index < 0) return activities.length;
  return placement === "before" ? index : index + 1;
}

function afterStageBlock(
  activities: ProgrammeActivity[],
  referenceId: string,
  start: number,
): number {
  const reference = activities.find((item) => item.activity_key === referenceId);
  const stageKey =
    reference?.kind === "stage" ? reference.activity_key : (reference?.parent_key ?? null);
  let insertAt = start;
  while (insertAt < activities.length && activities[insertAt]?.parent_key === stageKey) {
    insertAt += 1;
  }
  return insertAt;
}

function activitySlug(name: string): string {
  return name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "activity";
}

function uniqueActivityKey(activities: ProgrammeActivity[], key: string): string {
  const existing = new Set(activities.map((item) => item.activity_key));
  if (!existing.has(key)) return key;
  let suffix = 2;
  while (existing.has(`${key}-${suffix}`)) suffix += 1;
  return `${key}-${suffix}`;
}

export function previousProgrammeKey(
  activities: ProgrammeActivity[],
  activityKey: string,
): string | null {
  const index = activities.findIndex((item) => item.activity_key === activityKey);
  if (index <= 0) return null;
  return activities[index - 1]?.activity_key ?? null;
}

export function programmeDependencyWouldCycle(
  activities: ProgrammeActivity[],
  dependencies: ProgrammeDependency[],
  sourceActivityKey: string,
  targetActivityKey: string,
): boolean {
  const activityKeys = new Set(activities.map((item) => item.activity_key));
  if (
    sourceActivityKey === targetActivityKey ||
    !activityKeys.has(sourceActivityKey) ||
    !activityKeys.has(targetActivityKey)
  ) {
    return true;
  }
  const outgoing = new Map<string, string[]>();
  for (const dependency of dependencies) {
    const bucket = outgoing.get(dependency.source_activity_key) ?? [];
    bucket.push(dependency.target_activity_key);
    outgoing.set(dependency.source_activity_key, bucket);
  }
  const pending = [targetActivityKey];
  const seen = new Set<string>();
  while (pending.length) {
    const key = pending.pop()!;
    if (key === sourceActivityKey) return true;
    if (seen.has(key)) continue;
    seen.add(key);
    pending.push(...(outgoing.get(key) ?? []));
  }
  return false;
}

export type ProgrammeLink = {
  key: string;
  fromOffset: number;
  toOffset: number;
  fromIndex: number;
  toIndex: number;
  sourceEndpoint: DependencyEndpoint;
  targetEndpoint: DependencyEndpoint;
  lagDays: number;
  laneIndex: number;
};

export function programmeActivitySpan(
  spanStart: string,
  activity: ProgrammeActivity,
): { start: number; end: number } {
  const start = daysBetween(spanStart, activity.start_date);
  const duration = Math.max(
    activity.duration_days,
    activity.kind === "milestone" ? 0 : 1,
  );
  return { start, end: start + duration };
}

export function programmeLinks(
  activities: ProgrammeActivity[],
  dependencies: ProgrammeDependency[],
  spanStart: string,
): ProgrammeLink[] {
  const positions = new Map(
    activities.map((item, index) => [
      item.activity_key,
      { item, index, span: programmeActivitySpan(spanStart, item) },
    ]),
  );
  const links: ProgrammeLink[] = [];
  const lanes = new Map<string, number>();
  for (const dependency of dependencies) {
    const source = positions.get(dependency.source_activity_key);
    const target = positions.get(dependency.target_activity_key);
    if (!source || !target) continue;
    const fromOffset =
      dependency.source_endpoint === "start" ? source.span.start : source.span.end;
    const toOffset =
      dependency.target_endpoint === "start" ? target.span.start : target.span.end;
    const laneKey = `${dependency.source_endpoint}:${dependency.target_endpoint}:${Math.round(
      Math.min(fromOffset, toOffset) / 7,
    )}`;
    const laneIndex = lanes.get(laneKey) ?? 0;
    lanes.set(laneKey, laneIndex + 1);
    links.push({
      key: dependency.dependency_key,
      fromOffset,
      toOffset,
      fromIndex: source.index,
      toIndex: target.index,
      sourceEndpoint: dependency.source_endpoint,
      targetEndpoint: dependency.target_endpoint,
      lagDays: dependency.lag_days,
      laneIndex,
    });
  }
  return links;
}

export function ganttLinkPath(
  link: ProgrammeLink,
  rowHeight: number,
  linkY: number,
  xScale: number,
  stubX = 8,
): string {
  const x1 = link.fromOffset * xScale;
  const x2 = link.toOffset * xScale;
  const y1 = link.fromIndex * rowHeight + linkY;
  const y2 = link.toIndex * rowHeight + linkY;
  const sourceStub = x1 + (link.sourceEndpoint === "start" ? -stubX : stubX);
  const targetStub = x2 + (link.targetEndpoint === "start" ? -stubX : stubX);
  let trunk: number;
  if (link.sourceEndpoint === "start" && link.targetEndpoint === "start") {
    trunk = Math.min(sourceStub, targetStub) - stubX;
  } else if (link.sourceEndpoint === "finish" && link.targetEndpoint === "finish") {
    trunk = Math.max(sourceStub, targetStub) + stubX;
  } else if (link.sourceEndpoint === "finish" && link.targetEndpoint === "start") {
    trunk = sourceStub <= targetStub
      ? (sourceStub + targetStub) / 2
      : Math.max(sourceStub, targetStub) + stubX;
  } else {
    trunk = Math.min(sourceStub, targetStub) - stubX;
  }
  if (link.laneIndex > 0) {
    const laneOffset = link.laneIndex * Math.max(3, stubX * 0.55);
    const routesLeft =
      link.sourceEndpoint === "start" ||
      (link.sourceEndpoint === "finish" &&
        link.targetEndpoint === "start" &&
        sourceStub <= targetStub);
    trunk += routesLeft ? -laneOffset : laneOffset;
  }
  return `M ${x1} ${y1} H ${sourceStub} H ${trunk} V ${y2} H ${targetStub} H ${x2}`;
}

export function addDays(iso: string, days: number): string {
  const date = parseIsoDate(iso);
  date.setUTCDate(date.getUTCDate() + days);
  return toIsoDate(date);
}

export function daysBetween(start: string, end: string): number {
  const ms = parseIsoDate(end).getTime() - parseIsoDate(start).getTime();
  return Math.round(ms / 86_400_000);
}

export function parseIsoDate(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

export function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

const MONTH_YEAR = new Intl.DateTimeFormat("en-AU", {
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const DAY_MONTH = new Intl.DateTimeFormat("en-AU", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

export type ProgrammeAxisBand = {
  start: string;
  days: number;
  label: string;
  title?: string;
};

export type ProgrammeHeaderLayers = {
  major: ProgrammeAxisBand[];
  minor: ProgrammeAxisBand[];
};

const HEADER_CHAR_PX = 6;
const HEADER_PAD_PX = 2;
const MONTH_LETTERS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"] as const;
const MONTH_ABBREV2 = ["Ja", "Fe", "Mr", "Ap", "My", "Jn", "Jl", "Au", "Se", "Oc", "No", "De"] as const;
const MONTH_ABBREV3 = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

export function startOfMonth(iso: string): string {
  const date = parseIsoDate(iso);
  return toIsoDate(new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1)));
}

export function addMonths(iso: string, months: number): string {
  const date = parseIsoDate(iso);
  return toIsoDate(
    new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + months, 1)),
  );
}

export function startOfQuarter(iso: string): string {
  const date = parseIsoDate(iso);
  const month = Math.floor(date.getUTCMonth() / 3) * 3;
  return toIsoDate(new Date(Date.UTC(date.getUTCFullYear(), month, 1)));
}

export function startOfYear(iso: string): string {
  const date = parseIsoDate(iso);
  return toIsoDate(new Date(Date.UTC(date.getUTCFullYear(), 0, 1)));
}

export function formatMonthYear(iso: string): string {
  return MONTH_YEAR.format(parseIsoDate(iso));
}

export function formatDayMonth(iso: string): string {
  return DAY_MONTH.format(parseIsoDate(iso));
}

export function formatQuarterLabel(iso: string): string {
  const date = parseIsoDate(iso);
  return `Q${Math.floor(date.getUTCMonth() / 3) + 1} ${date.getUTCFullYear()}`;
}

export function formatYear(iso: string): string {
  return String(parseIsoDate(iso).getUTCFullYear());
}

function formatYearShort(iso: string): string {
  return `'${String(parseIsoDate(iso).getUTCFullYear()).slice(2)}`;
}

export function formatMonthLetter(iso: string): string {
  return MONTH_LETTERS[parseIsoDate(iso).getUTCMonth()];
}

export function formatWeekOfMonth(iso: string): string {
  return String(Math.floor((parseIsoDate(iso).getUTCDate() - 1) / 7) + 1);
}

export function formatCompactDate(iso: string): string {
  const date = parseIsoDate(iso);
  return `${date.getUTCDate()} ${MONTH_ABBREV3[date.getUTCMonth()]} ${String(date.getUTCFullYear()).slice(2)}`;
}

function headerLabelFits(text: string, widthPx: number): boolean {
  return text.length * HEADER_CHAR_PX + HEADER_PAD_PX <= widthPx;
}

export function programmeScaleBands(
  start: string,
  end: string,
  scale: ProgrammeScale,
): ProgrammeAxisBand[] {
  if (end <= start) return [];
  if (scale === "quarter") {
    return collectBands(start, end, startOfQuarter, (cursor) => addMonths(startOfQuarter(cursor), 3), formatQuarterLabel);
  }
  return collectBands(start, end, startOfMonth, (cursor) => addMonths(startOfMonth(cursor), 1), formatMonthYear);
}

export function programmeWeekTicks(start: string, end: string): ProgrammeAxisBand[] {
  if (end <= start) return [];
  const ticks: ProgrammeAxisBand[] = [];
  let cursor = start;
  while (cursor < end) {
    const next = addDays(cursor, 7);
    const tickEnd = next < end ? next : end;
    ticks.push({
      start: cursor,
      days: daysBetween(cursor, tickEnd),
      label: formatDayMonth(cursor),
    });
    cursor = tickEnd;
  }
  return ticks;
}

export function programmeHeaderLayers(
  start: string,
  end: string,
  scale: ProgrammeScale,
  pxPerDay: number,
): ProgrammeHeaderLayers {
  if (end <= start) return { major: [], minor: [] };
  if (scale === "week") return weekHeaderLayers(start, end, pxPerDay);
  if (scale === "quarter") return quarterHeaderLayers(start, end, pxPerDay);
  return monthHeaderLayers(start, end, pxPerDay);
}

function weekHeaderLayers(
  start: string,
  end: string,
  pxPerDay: number,
): ProgrammeHeaderLayers {
  const months = collectBands(
    start,
    end,
    startOfMonth,
    (cursor) => addMonths(startOfMonth(cursor), 1),
    formatMonthYear,
  );
  const avgMonthPx =
    months.reduce((sum, band) => sum + band.days * pxPerDay, 0) / Math.max(months.length, 1);
  const monthMajors = compactMonthMajors(months, pxPerDay);
  const yearVisible = monthMajors.some((band) => /\d/.test(band.label));
  const major =
    avgMonthPx >= 10 && (yearVisible || avgMonthPx >= 20)
      ? titled(monthMajors, formatMonthYear)
      : titled(
          compactBands(quarterBands(start, end), pxPerDay, quarterMajorCandidates),
          formatQuarterLabel,
        );
  const ticks = programmeWeekTicks(start, end).map((tick) => ({
    ...tick,
    title: `${formatDayMonth(tick.start)} ${parseIsoDate(tick.start).getUTCFullYear()}`,
  }));
  return {
    major,
    minor: compactBands(ticks, pxPerDay, weekMinorCandidates),
  };
}

function monthHeaderLayers(
  start: string,
  end: string,
  pxPerDay: number,
): ProgrammeHeaderLayers {
  return {
    major: titled(
      compactBands(yearBands(start, end), pxPerDay, yearCandidates),
      formatYear,
    ),
    minor: titled(
      compactBands(monthBands(start, end), pxPerDay, monthMinorCandidates),
      formatMonthYear,
    ),
  };
}

function quarterHeaderLayers(
  start: string,
  end: string,
  pxPerDay: number,
): ProgrammeHeaderLayers {
  return {
    major: titled(
      compactBands(yearBands(start, end), pxPerDay, yearCandidates),
      formatYear,
    ),
    minor: titled(
      compactBands(quarterBands(start, end), pxPerDay, quarterMinorCandidates),
      formatQuarterLabel,
    ),
  };
}

function monthBands(start: string, end: string): ProgrammeAxisBand[] {
  return collectBands(
    start,
    end,
    startOfMonth,
    (cursor) => addMonths(startOfMonth(cursor), 1),
    formatMonthYear,
  );
}

function quarterBands(start: string, end: string): ProgrammeAxisBand[] {
  return collectBands(
    start,
    end,
    startOfQuarter,
    (cursor) => addMonths(startOfQuarter(cursor), 3),
    formatQuarterLabel,
  );
}

function yearBands(start: string, end: string): ProgrammeAxisBand[] {
  return collectBands(
    start,
    end,
    startOfYear,
    (cursor) => addMonths(startOfYear(cursor), 12),
    formatYear,
  );
}

function monthMinorCandidates(band: ProgrammeAxisBand): string[] {
  const month = parseIsoDate(band.start).getUTCMonth();
  return [MONTH_ABBREV3[month], MONTH_ABBREV2[month], MONTH_LETTERS[month]];
}

function quarterMinorCandidates(band: ProgrammeAxisBand): string[] {
  const quarter = Math.floor(parseIsoDate(band.start).getUTCMonth() / 3) + 1;
  return [`Q${quarter}`, String(quarter)];
}

function quarterMajorCandidates(band: ProgrammeAxisBand): string[] {
  const date = parseIsoDate(band.start);
  const quarter = Math.floor(date.getUTCMonth() / 3) + 1;
  const year = date.getUTCFullYear();
  return [`Q${quarter} ${year}`, `Q${quarter} '${String(year).slice(2)}`, `Q${quarter}`, String(quarter)];
}

function yearCandidates(band: ProgrammeAxisBand): string[] {
  return [formatYear(band.start), formatYearShort(band.start)];
}

function weekMinorCandidates(band: ProgrammeAxisBand): string[] {
  const day = String(parseIsoDate(band.start).getUTCDate());
  return [formatDayMonth(band.start), day, formatWeekOfMonth(band.start)];
}

function monthMajorCandidates(band: ProgrammeAxisBand, includeYear: boolean): string[] {
  const date = parseIsoDate(band.start);
  const month = date.getUTCMonth();
  const year = date.getUTCFullYear();
  const letter = MONTH_LETTERS[month];
  const two = MONTH_ABBREV2[month];
  const three = MONTH_ABBREV3[month];
  if (!includeYear) return [three, two, letter];
  return [
    `${three} ${year}`,
    `${three} '${String(year).slice(2)}`,
    `${letter}${String(year).slice(2)}`,
    three,
    two,
    letter,
  ];
}

function compactMonthMajors(
  months: ProgrammeAxisBand[],
  pxPerDay: number,
): ProgrammeAxisBand[] {
  const visible = compactBands(months, pxPerDay, (band) => monthMajorCandidates(band, false));
  const seenYears = new Set<number>();
  return visible.map((band) => {
    const year = parseIsoDate(band.start).getUTCFullYear();
    if (seenYears.has(year)) return band;
    const widthPx = band.days * pxPerDay;
    const withYear = pickFittingLabel(monthMajorCandidates(band, true), widthPx);
    if (withYear && /\d/.test(withYear)) {
      seenYears.add(year);
      return { ...band, label: withYear };
    }
    return band;
  });
}

function titled(
  bands: ProgrammeAxisBand[],
  titleFor: (iso: string) => string,
): ProgrammeAxisBand[] {
  return bands.map((band) => ({
    ...band,
    title: band.title ?? titleFor(band.start),
  }));
}

function pickFittingLabel(candidates: string[], widthPx: number): string | null {
  return candidates.find((text) => headerLabelFits(text, widthPx)) ?? null;
}

function labelStride(widthPx: number, minLabelPx: number): number {
  return Math.max(1, Math.ceil(minLabelPx / Math.max(widthPx, 1)));
}

function compactBands(
  bands: ProgrammeAxisBand[],
  pxPerDay: number,
  candidatesFor: (band: ProgrammeAxisBand) => string[],
): ProgrammeAxisBand[] {
  const resolved = bands.map((band) => {
    const widthPx = band.days * pxPerDay;
    return { band, widthPx, label: pickFittingLabel(candidatesFor(band), widthPx) };
  });
  const fitted = resolved.filter((item) => item.label);
  if (fitted.length >= Math.ceil(bands.length / 2) || bands.length <= 2) {
    return fitted.map((item) => ({ ...item.band, label: item.label! }));
  }
  const shortestPx = Math.min(
    ...bands.map((band) => {
      const shortest = candidatesFor(band).at(-1) ?? "1";
      return shortest.length * HEADER_CHAR_PX + HEADER_PAD_PX;
    }),
  );
  const avgWidth =
    resolved.reduce((sum, item) => sum + item.widthPx, 0) / Math.max(bands.length, 1);
  const stride = labelStride(avgWidth, shortestPx);
  return bands.flatMap((band, index) => {
    if (index % stride !== 0) return [];
    const widthPx = band.days * pxPerDay * stride;
    const label = pickFittingLabel(candidatesFor(band), widthPx);
    return label ? [{ ...band, label }] : [];
  });
}

function collectBands(
  start: string,
  end: string,
  origin: (iso: string) => string,
  next: (iso: string) => string,
  label: (iso: string) => string,
): ProgrammeAxisBand[] {
  const bands: ProgrammeAxisBand[] = [];
  let cursor = start;
  while (cursor < end) {
    const boundary = next(cursor);
    const bandEnd = boundary < end ? boundary : end;
    bands.push({
      start: cursor,
      days: Math.max(daysBetween(cursor, bandEnd), 1),
      label: label(origin(cursor)),
    });
    cursor = bandEnd;
  }
  return bands;
}

export function programmeSpan(activities: ProgrammeActivity[]): {
  start: string;
  end: string;
} {
  if (!activities.length) {
    const today = toIsoDate(new Date());
    return { start: today, end: addDays(today, 1) };
  }
  const starts = activities.map((item) => item.start_date);
  const ends = activities.map((item) => item.finish_date || item.start_date);
  const start = starts.reduce((min, value) => (value < min ? value : min));
  const end = ends.reduce((max, value) => (value > max ? value : max));
  return { start, end: end <= start ? addDays(start, 1) : end };
}

export function stripProgrammeSectionBody(markdown: string): string {
  const parts = markdown.split(/(?=^## )/m);
  return parts
    .map((part) => {
      const match = /^##\s+(.+?)\s*$/m.exec(part);
      if (!match) return part;
      const heading = match[1].trim();
      if (!PROGRAMME_HEADINGS.has(heading.toLowerCase())) return part;
      return `## ${heading}\n\n`;
    })
    .join("")
    .replace(/\n{3,}/g, "\n\n");
}

export function insertAfterProgrammeHeading(
  markdown: string,
  figure: string,
): string {
  const match = PROGRAMME_HEADING_RE.exec(markdown);
  if (!match || match.index === undefined) return `${markdown.trimEnd()}\n\n${figure}\n`;
  const headingEnd = markdown.indexOf("\n", match.index);
  const splitAt = headingEnd === -1 ? markdown.length : headingEnd + 1;
  return `${markdown.slice(0, splitAt)}\n${figure}\n${markdown.slice(splitAt)}`;
}
