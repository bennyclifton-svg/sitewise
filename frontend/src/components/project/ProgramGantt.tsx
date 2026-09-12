import {
  memo,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactElement,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import {
  ChevronDown,
  ChevronRight,
  GripVertical,
  Link2,
  Plus,
  Timer,
  Trash,
  Unlink,
  X,
} from "lucide-react";

import { ProgrammeDateField } from "@/components/project/ProgrammeDateField";
import { ProgrammeSequenceLagDialog } from "@/components/project/ProgrammeSequenceLagDialog";
import { Button } from "@/components/ui/button";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuLabel,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { Input } from "@/components/ui/input";
import {
  addDays,
  applyProgrammeOperationsLocally,
  daysBetween,
  formatCompactDate,
  programmeBulkDeleteOperations,
  programmeDependencyKey,
  programmeDependencyWouldCycle,
  programmeRowMove,
  programmeHeaderLayers,
  programmeSequentialDependencies,
  programmeSequentialLagOperations,
  programmeSequentialLinkOperations,
  programmeSequentialUnlinkOperations,
  programmeSpan,
  programmeActivitySpan,
  programmeLinks,
  ganttLinkPath,
  type ProgrammeActivity,
  type ProgrammeAxisBand,
  type ProgrammeDependency,
  type DependencyEndpoint,
  type ProgrammeOperation,
  type ProgrammeScale,
  type ProgrammeSequencePlan,
  type ProgrammeState,
} from "@/lib/programme";
import { cn } from "@/lib/utils";

const ROW_HEIGHT = 24;
const BAR_HEIGHT = 16;
const BAR_TOP = 4;
const LINK_Y = 12;
const DEPENDENCY_EDITOR_SPACE = 168;
const DEPENDENCY_EDITOR_HALF_WIDTH = 96;
const GRID_MINOR =
  "bg-[color-mix(in_oklch,var(--sw-text-tertiary)_11%,transparent)]";
const GRID_MAJOR =
  "bg-[color-mix(in_oklch,var(--sw-text-tertiary)_20%,transparent)]";
const GRID_ROW =
  "border-[color-mix(in_oklch,var(--sw-text-tertiary)_12%,transparent)]";
const NAME_WIDTH = 220;
const DATE_WIDTH = 88;
const DURATION_WIDTH = 48;
const PLUS_WIDTH = 24;
const TRASH_WIDTH = 24;
const GRIP_WIDTH = 18;
const SCALE_PX: Record<ProgrammeScale, number> = {
  week: 18,
  month: 6,
  quarter: 2,
};
const FIGURE_SCALES: ProgrammeScale[] = ["month", "quarter"];
const SCHEDULE_PANE = NAME_WIDTH + DATE_WIDTH + DURATION_WIDTH;
const ACTION_PANE = PLUS_WIDTH + TRASH_WIDTH;
const ROW_TEXT = "text-[10px] leading-5 md:text-[10px]";

type DependencyAnchor = {
  activityKey: string;
  endpoint: DependencyEndpoint;
};

const DEPENDENCY_RELATIONSHIPS = [
  {
    code: "FF",
    label: "Finish to finish",
    sourceEndpoint: "finish",
    targetEndpoint: "finish",
  },
  {
    code: "SF",
    label: "Start to finish",
    sourceEndpoint: "start",
    targetEndpoint: "finish",
  },
  {
    code: "FS",
    label: "Finish to start",
    sourceEndpoint: "finish",
    targetEndpoint: "start",
  },
  {
    code: "SS",
    label: "Start to start",
    sourceEndpoint: "start",
    targetEndpoint: "start",
  },
] as const;

type DependencyRelationshipCode = (typeof DEPENDENCY_RELATIONSHIPS)[number]["code"];

function chartBoxStyle(
  fitted: boolean,
  panePx: number,
  offsetDays: number,
  sizeDays: number,
  spanDays: number,
  pxPerDay: number,
  minUnfittedPx = 0,
): { left: number | string; width: number | string } {
  if (!fitted) {
    return {
      left: panePx + offsetDays * pxPerDay,
      width: Math.max(sizeDays * pxPerDay, minUnfittedPx),
    };
  }
  const span = Math.max(spanDays, 1);
  if (sizeDays <= 0 && minUnfittedPx > 0) {
    return {
      left: `calc(${panePx}px + (100% - ${panePx}px) * ${offsetDays / span})`,
      width: minUnfittedPx,
    };
  }
  return {
    left: `calc(${panePx}px + (100% - ${panePx}px) * ${offsetDays / span})`,
    width: `calc((100% - ${panePx}px) * ${sizeDays / span})`,
  };
}

function milestoneBoxStyle(
  milestone: boolean,
  style: { left: number | string; width: number | string },
): { left: number | string; width: number | string } {
  if (!milestone) return style;
  return {
    left:
      typeof style.left === "number"
        ? style.left - 6
        : `calc(${style.left} - 6px)`,
    width: 12,
  };
}

export function ProgramGantt({
  state,
  mode,
  onOperate,
  onScaleChange,
  onCollapsedChange,
  active = true,
}: {
  state: ProgrammeState;
  mode: "edit" | "figure";
  onOperate?: (operations: ProgrammeOperation[]) => void;
  onScaleChange?: (scale: ProgrammeScale) => void;
  onCollapsedChange?: (stageKeys: string[]) => void;
  /** False while the workbench is kept mounted but hidden. */
  active?: boolean;
}) {
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const [surfaceWidth, setSurfaceWidth] = useState(0);
  const [fitToScreen, setFitToScreen] = useState(mode === "edit");
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const [modifierLinking, setModifierLinking] = useState(false);
  const [pendingAnchor, setPendingAnchor] = useState<DependencyAnchor | null>(null);
  const [selectedDependencyKey, setSelectedDependencyKey] = useState<string | null>(null);
  const [previewUpdate, setPreviewUpdate] = useState<{
    activityKey: string;
    values: Record<string, unknown>;
  } | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [selectionAnchor, setSelectionAnchor] = useState<string | null>(null);
  const [sequenceLagOpen, setSequenceLagOpen] = useState(false);
  const [rowDrag, setRowDrag] = useState<{
    key: string;
    overKey: string;
    placement: "before" | "after";
  } | null>(null);
  const stageKeys = useMemo(
    () => state.activities.filter((item) => item.kind === "stage").map((item) => item.activity_key),
    [state.activities],
  );
  const dependencies = useMemo(() => state.dependencies ?? [], [state.dependencies]);
  const collapsedStages = useMemo(
    () =>
      new Set(
        state.collapsed_stage_keys.filter((key) => stageKeys.includes(key)),
      ),
    [stageKeys, state.collapsed_stage_keys],
  );
  const visibleActivities = useMemo(
    () =>
      state.activities.filter(
        (item) => item.kind === "stage" || !item.parent_key || !collapsedStages.has(item.parent_key),
      ),
    [collapsedStages, state.activities],
  );
  const previewState = useMemo(() => {
    if (!previewUpdate) return state;
    const activity = state.activities.find(
      (item) => item.activity_key === previewUpdate.activityKey,
    );
    if (!activity) return state;
    return applyProgrammeOperationsLocally(state, [
      {
        operation: "UPDATE",
        target_type: activity.kind,
        target_id: activity.activity_key,
        values: previewUpdate.values,
      },
    ]);
  }, [previewUpdate, state]);
  const previewByKey = useMemo(
    () => new Map(previewState.activities.map((item) => [item.activity_key, item])),
    [previewState.activities],
  );
  const linkActivities = useMemo(
    () => visibleActivities.map((item) => previewByKey.get(item.activity_key) ?? item),
    [previewByKey, visibleActivities],
  );
  const renderedActivities = useMemo(
    () => visibleActivities.map((item) => previewByKey.get(item.activity_key) ?? item),
    [previewByKey, visibleActivities],
  );
  const activityKeys = useMemo(
    () => new Set(visibleActivities.map((item) => item.activity_key)),
    [visibleActivities],
  );
  const visibleSelected = useMemo(() => {
    const next = new Set([...selectedKeys].filter((key) => activityKeys.has(key)));
    return next.size === selectedKeys.size ? selectedKeys : next;
  }, [selectedKeys, activityKeys]);
  const visibleAnchor =
    selectionAnchor && activityKeys.has(selectionAnchor) ? selectionAnchor : null;
  const sequenceDependencies = useMemo(
    () =>
      programmeSequentialDependencies(
        state.activities,
        dependencies,
        visibleSelected,
      ),
    [dependencies, state.activities, visibleSelected],
  );
  const sequencePlans = useMemo(
    () =>
      new Map<DependencyRelationshipCode, ProgrammeSequencePlan>(
        DEPENDENCY_RELATIONSHIPS.map((option) => [
          option.code,
          programmeSequentialLinkOperations(
            state.activities,
            dependencies,
            visibleSelected,
            option.sourceEndpoint,
            option.targetEndpoint,
          ),
        ]),
      ),
    [dependencies, state.activities, visibleSelected],
  );
  const commonSequenceLag =
    sequenceDependencies.length > 0 &&
    sequenceDependencies.every(
      (dependency) => dependency.lag_days === sequenceDependencies[0]?.lag_days,
    )
      ? (sequenceDependencies[0]?.lag_days ?? null)
      : null;
  const span = useMemo(() => programmeSpan(state.activities), [state.activities]);
  const spanDays = Math.max(daysBetween(span.start, span.end), 1);
  const fitted = mode === "figure" || fitToScreen;
  const leftPane = mode === "figure" ? SCHEDULE_PANE : SCHEDULE_PANE + ACTION_PANE;
  const headerHeight = 44;
  const measuredChart = Math.max((surfaceWidth || 720) - leftPane, 80);
  const pxPerDay = fitted ? measuredChart / spanDays : SCALE_PX[state.view_scale];
  const chartWidth = fitted ? measuredChart : Math.max(spanDays * pxPerDay, 320);
  const editorSpace =
    mode === "edit" && selectedDependencyKey ? DEPENDENCY_EDITOR_SPACE : 0;

  useEffect(() => {
    const node = surfaceRef.current;
    if (!active || !node) return;
    const readWidth = () => {
      const width = node.getBoundingClientRect().width;
      if (width) {
        setSurfaceWidth((current) => (current === width ? current : width));
      }
    };
    readWidth();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width ?? 0;
      setSurfaceWidth((current) => (current === width ? current : width));
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [active]);

  useEffect(() => {
    if (mode !== "edit") return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Control" || event.key === "Meta") setModifierLinking(true);
      if (event.key === "Escape") {
        setSelectedKeys(new Set());
        setPendingAnchor(null);
        setSelectedDependencyKey(null);
      }
    };
    const onKeyUp = (event: KeyboardEvent) => {
      if (event.key === "Control" || event.key === "Meta") setModifierLinking(false);
    };
    const onBlur = () => setModifierLinking(false);
    window.addEventListener("keydown", onKey);
    window.addEventListener("keyup", onKeyUp);
    window.addEventListener("blur", onBlur);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("blur", onBlur);
    };
  }, [mode]);

  function update(activity: ProgrammeActivity, values: Record<string, unknown>) {
    onOperate?.([
      {
        operation: "UPDATE",
        target_type: activity.kind,
        target_id: activity.activity_key,
        values,
      },
    ]);
  }

  function remove(activity: ProgrammeActivity) {
    onOperate?.([
      {
        operation: "DELETE",
        target_type: activity.kind,
        target_id: activity.activity_key,
      },
    ]);
    if (focusKey === activity.activity_key) setFocusKey(null);
    setSelectedKeys((current) => {
      if (!current.has(activity.activity_key)) return current;
      const next = new Set(current);
      next.delete(activity.activity_key);
      return next;
    });
  }

  function removeSelected() {
    const operations = programmeBulkDeleteOperations(state.activities, visibleSelected);
    if (!operations.length) return;
    onOperate?.(operations);
    setSelectedKeys(new Set());
    setFocusKey(null);
  }

  function confirmRemoveSelected() {
    const operations = programmeBulkDeleteOperations(state.activities, visibleSelected);
    if (!operations.length) return;
    const selectedStages = new Set(
      state.activities
        .filter(
          (activity) =>
            activity.kind === "stage" && visibleSelected.has(activity.activity_key),
        )
        .map((activity) => activity.activity_key),
    );
    const childCount = state.activities.filter(
      (activity) => activity.parent_key && selectedStages.has(activity.parent_key),
    ).length;
    const rowLabel = `${visibleSelected.size} selected row${visibleSelected.size === 1 ? "" : "s"}`;
    const childLabel = childCount
      ? ` and ${childCount} child row${childCount === 1 ? "" : "s"}`
      : "";
    if (
      window.confirm(
        `Delete ${rowLabel}${childLabel}? This action cannot be undone.`,
      )
    ) {
      removeSelected();
    }
  }

  function handleRowContextMenu(key: string) {
    if (!visibleSelected.has(key)) setSelectedKeys(new Set([key]));
    setSelectionAnchor(key);
    setFocusKey(key);
    setPendingAnchor(null);
    setSelectedDependencyKey(null);
  }

  function linkSelected(code: DependencyRelationshipCode) {
    const plan = sequencePlans.get(code);
    if (!plan || plan.wouldCycle || plan.exceedsLimit || !plan.operations.length) return;
    onOperate?.(plan.operations);
  }

  function applySequenceLag(lagDays: number) {
    const operations = programmeSequentialLagOperations(
      state.activities,
      dependencies,
      visibleSelected,
      lagDays,
    );
    if (operations.length) onOperate?.(operations);
  }

  function unlinkSelected() {
    const operations = programmeSequentialUnlinkOperations(
      state.activities,
      dependencies,
      visibleSelected,
    );
    if (operations.length) onOperate?.(operations);
  }

  function handleRowClick(event: ReactMouseEvent, key: string) {
    const target = event.target as HTMLElement;
    const fromControl = Boolean(
      target.closest("input, button, [data-interactive], [role='separator']"),
    );
    const additive = event.ctrlKey || event.metaKey;
    if (fromControl && !event.shiftKey && !additive) {
      setFocusKey(key);
      return;
    }
    const keys = visibleActivities.map((item) => item.activity_key);
    if (event.shiftKey) {
      const anchor =
        visibleAnchor && keys.includes(visibleAnchor) ? visibleAnchor : key;
      const start = keys.indexOf(anchor);
      const end = keys.indexOf(key);
      if (start >= 0 && end >= 0) {
        const range = keys.slice(Math.min(start, end), Math.max(start, end) + 1);
        setSelectedKeys((current) => {
          const next = additive ? new Set(current) : new Set<string>();
          for (const item of range) next.add(item);
          return next;
        });
      }
      setFocusKey(key);
      return;
    }
    if (additive) {
      setSelectedKeys((current) => {
        const next = new Set(current);
        if (next.has(key)) next.delete(key);
        else next.add(key);
        return next;
      });
      setSelectionAnchor(key);
      setFocusKey(key);
      return;
    }
    setSelectedKeys(new Set([key]));
    setSelectionAnchor(key);
    setFocusKey(key);
  }

  function addRowAfter(row: ProgrammeActivity) {
    if (row.kind === "stage") {
      onOperate?.([
        {
          operation: "ADD",
          target_type: "stage",
          reference_id: row.activity_key,
          placement: "after",
          values: {
            name: "New parent group",
            start_date: row.finish_date || row.start_date,
            duration_days: 30,
          },
        },
      ]);
      return;
    }
    const parent = row.parent_key;
    if (!parent) return;
    onOperate?.([
      {
        operation: "ADD",
        target_type: "activity",
        reference_id: row.activity_key,
        placement: "after",
        values: {
          name: "New activity",
          parent_key: parent,
          start_date: row.start_date,
          duration_days: 14,
        },
      },
    ]);
  }

  function toggleStage(stageKey: string) {
    const next = new Set(collapsedStages);
    if (next.has(stageKey)) next.delete(stageKey);
    else next.add(stageKey);
    onCollapsedChange?.(stageKeys.filter((key) => next.has(key)));
  }

  function toggleAllStages() {
    const allCollapsed = stageKeys.length > 0 && stageKeys.every((key) => collapsedStages.has(key));
    onCollapsedChange?.(allCollapsed ? [] : stageKeys);
  }

  function chooseDependencyAnchor(anchor: DependencyAnchor) {
    if (!pendingAnchor) {
      setPendingAnchor(anchor);
      setSelectedDependencyKey(null);
      return;
    }
    if (
      pendingAnchor.activityKey === anchor.activityKey &&
      pendingAnchor.endpoint === anchor.endpoint
    ) {
      setPendingAnchor(null);
      return;
    }
    if (
      programmeDependencyWouldCycle(
        state.activities,
        dependencies,
        pendingAnchor.activityKey,
        anchor.activityKey,
      )
    ) {
      setPendingAnchor(anchor);
      return;
    }
    const dependencyKey = programmeDependencyKey(
      pendingAnchor.activityKey,
      pendingAnchor.endpoint,
      anchor.activityKey,
      anchor.endpoint,
    );
    onOperate?.([
      {
        operation: "ADD",
        target_type: "dependency",
        values: {
          dependency_key: dependencyKey,
          source_activity_key: pendingAnchor.activityKey,
          target_activity_key: anchor.activityKey,
          source_endpoint: pendingAnchor.endpoint,
          target_endpoint: anchor.endpoint,
          lag_days: 0,
        },
      },
    ]);
    setPendingAnchor(null);
    setSelectedDependencyKey(dependencyKey);
  }

  function updateDependency(dependency: ProgrammeDependency, lagDays: number) {
    onOperate?.([
      {
        operation: "UPDATE",
        target_type: "dependency",
        target_id: dependency.dependency_key,
        values: { lag_days: Math.max(0, lagDays) },
      },
    ]);
  }

  function changeDependencyRelationship(
    dependency: ProgrammeDependency,
    sourceEndpoint: DependencyEndpoint,
    targetEndpoint: DependencyEndpoint,
  ) {
    const nextKey = programmeDependencyKey(
      dependency.source_activity_key,
      sourceEndpoint,
      dependency.target_activity_key,
      targetEndpoint,
    );
    if (nextKey === dependency.dependency_key) return;
    onOperate?.([
      {
        operation: "DELETE",
        target_type: "dependency",
        target_id: dependency.dependency_key,
      },
      {
        operation: "ADD",
        target_type: "dependency",
        values: {
          dependency_key: nextKey,
          source_activity_key: dependency.source_activity_key,
          target_activity_key: dependency.target_activity_key,
          source_endpoint: sourceEndpoint,
          target_endpoint: targetEndpoint,
          lag_days: dependency.lag_days,
        },
      },
    ]);
    setSelectedDependencyKey(nextKey);
  }

  function removeDependency(dependency: ProgrammeDependency) {
    onOperate?.([
      {
        operation: "DELETE",
        target_type: "dependency",
        target_id: dependency.dependency_key,
      },
    ]);
    setSelectedDependencyKey(null);
  }

  function beginRowDrag(event: ReactPointerEvent, sourceKey: string) {
    event.preventDefault();
    event.stopPropagation();
    const surface = surfaceRef.current;
    if (!surface) return;
    const readTarget = (clientY: number) => {
      const top = surface.getBoundingClientRect().top + headerHeight;
      const raw = (clientY - top) / ROW_HEIGHT;
      const index = Math.max(0, Math.min(visibleActivities.length - 1, Math.floor(raw)));
      return {
        overKey: visibleActivities[index]?.activity_key ?? sourceKey,
        placement: raw - index < 0.5 ? ("before" as const) : ("after" as const),
      };
    };
    let latest = { key: sourceKey, ...readTarget(event.clientY) };
    setRowDrag(latest);
    const onMovePointer = (moveEvent: PointerEvent) => {
      latest = { key: sourceKey, ...readTarget(moveEvent.clientY) };
      setRowDrag(latest);
    };
    const onUp = () => {
      window.removeEventListener("pointermove", onMovePointer);
      window.removeEventListener("pointerup", onUp);
      const operation = programmeRowMove(
        state.activities,
        latest.key,
        latest.overKey,
        latest.placement,
      );
      setRowDrag(null);
      if (operation) onOperate?.([operation]);
    };
    window.addEventListener("pointermove", onMovePointer);
    window.addEventListener("pointerup", onUp);
  }

  const chart = (
    <div
      ref={surfaceRef}
      className={cn(
        "program-gantt-surface min-w-0 overflow-hidden border",
        fitted ? "w-full" : "overflow-x-auto",
      )}
    >
      <div
        className="relative"
        style={{
          minWidth: fitted ? "100%" : leftPane + chartWidth,
          height:
            headerHeight +
            ROW_HEIGHT * Math.max(visibleActivities.length, 1) +
            editorSpace,
        }}
      >
        <GanttAxis
          start={span.start}
          days={spanDays}
          scale={state.view_scale}
          leftPane={leftPane}
          headerHeight={headerHeight}
          fitted={fitted}
          pxPerDay={pxPerDay}
          showScheduleColumns
          allStagesCollapsed={
            stageKeys.length > 0 && stageKeys.every((key) => collapsedStages.has(key))
          }
          onToggleAllStages={mode === "edit" ? toggleAllStages : undefined}
          selectedCount={mode === "edit" ? visibleSelected.size : 0}
          onDeleteSelected={mode === "edit" ? removeSelected : undefined}
        />
        <GanttGrid
          start={span.start}
          days={spanDays}
          scale={state.view_scale}
          leftPane={leftPane}
          headerHeight={headerHeight}
          fitted={fitted}
          pxPerDay={pxPerDay}
          rowCount={visibleActivities.length}
        />
        <GanttLinks
          activities={linkActivities}
          dependencies={previewState.dependencies ?? dependencies}
          spanStart={span.start}
          spanDays={spanDays}
          fitted={fitted}
          pxPerDay={pxPerDay}
          leftPane={leftPane}
          headerHeight={headerHeight}
          interactive={mode === "edit"}
          linkingActive={modifierLinking || pendingAnchor !== null}
          selectedDependencyKey={selectedDependencyKey}
          onSelectDependency={setSelectedDependencyKey}
        />
        {renderedActivities.map((activity, index) => (
          <ProgrammeRowContextMenu
            key={activity.activity_key}
            interactive={mode === "edit"}
            selectedCount={visibleSelected.size}
            sequencePlans={sequencePlans}
            sequenceLinkCount={sequenceDependencies.length}
            onLink={linkSelected}
            onSetLag={() => setSequenceLagOpen(true)}
            onUnlink={unlinkSelected}
            onDelete={confirmRemoveSelected}
          >
            <GanttRow
              activity={activity}
              index={index}
              spanStart={span.start}
              spanDays={spanDays}
              focused={focusKey === activity.activity_key}
              selected={visibleSelected.has(activity.activity_key)}
              previewed={previewUpdate?.activityKey === activity.activity_key}
              interactive={mode === "edit"}
              fitted={fitted}
              pxPerDay={pxPerDay}
              leftPane={leftPane}
              headerHeight={headerHeight}
              hideRowDelete={visibleSelected.size > 1}
              collapsed={collapsedStages.has(activity.activity_key)}
              onRowClick={
                mode === "edit"
                  ? (event) => handleRowClick(event, activity.activity_key)
                  : undefined
              }
              onContextMenu={
                mode === "edit"
                  ? () => handleRowContextMenu(activity.activity_key)
                  : undefined
              }
              dropPlacement={
                rowDrag?.overKey === activity.activity_key ? rowDrag.placement : null
              }
              dragging={rowDrag?.key === activity.activity_key}
              onRename={(name) => update(activity, { name })}
              onMove={(start) => update(activity, { start_date: start })}
              onResize={(days) => update(activity, { duration_days: days })}
              onResizeStart={(start, days) =>
                update(activity, { start_date: start, duration_days: days })
              }
              onPreview={(values) =>
                setPreviewUpdate(
                  values ? { activityKey: activity.activity_key, values } : null,
                )
              }
              onDelete={() => remove(activity)}
              onAdd={() => addRowAfter(activity)}
              onToggleCollapse={() => toggleStage(activity.activity_key)}
              linkingActive={modifierLinking || pendingAnchor !== null}
              pendingAnchor={pendingAnchor}
              onChooseAnchor={(endpoint) =>
                chooseDependencyAnchor({ activityKey: activity.activity_key, endpoint })
              }
              onReorder={(event) => beginRowDrag(event, activity.activity_key)}
            />
          </ProgrammeRowContextMenu>
        ))}
        {mode === "edit" ? (
          <DependencyEditor
            key={selectedDependencyKey ?? "no-dependency"}
            dependency={dependencies.find(
              (item) => item.dependency_key === selectedDependencyKey,
            )}
            activities={visibleActivities}
            spanStart={span.start}
            spanDays={spanDays}
            fitted={fitted}
            pxPerDay={pxPerDay}
            leftPane={leftPane}
            headerHeight={headerHeight}
            onChangeRelationship={changeDependencyRelationship}
            onChangeLag={updateDependency}
            onRemove={removeDependency}
            onClose={() => setSelectedDependencyKey(null)}
          />
        ) : null}
      </div>
    </div>
  );

  if (mode === "figure") {
    return (
      <div className="flex min-w-0 flex-col gap-2">
        <div className="flex print:hidden">
          <div className="flex overflow-hidden border">
            {FIGURE_SCALES.map((scale) => (
              <Button
                key={scale}
                type="button"
                size="sm"
                variant={state.view_scale === scale ? "default" : "ghost"}
                className="rounded-none capitalize"
                onClick={() => onScaleChange?.(scale)}
              >
                {scale}
              </Button>
            ))}
          </div>
        </div>
        {chart}
      </div>
    );
  }

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex overflow-hidden border">
          {(["week", "month", "quarter"] as const).map((scale) => (
            <Button
              key={scale}
              type="button"
              size="sm"
              variant={state.view_scale === scale ? "default" : "ghost"}
              className="rounded-none capitalize"
              onClick={() => onScaleChange?.(scale)}
            >
              {scale}
            </Button>
          ))}
        </div>
        <Button
          type="button"
          size="sm"
          variant={fitToScreen ? "default" : "outline"}
          aria-pressed={fitToScreen}
          onClick={() => setFitToScreen((current) => !current)}
        >
          Fit to screen
        </Button>
      </div>
      {chart}
      {sequenceLagOpen ? (
        <ProgrammeSequenceLagDialog
          open
          rowCount={visibleSelected.size}
          linkCount={sequenceDependencies.length}
          initialLag={commonSequenceLag}
          onOpenChange={setSequenceLagOpen}
          onApply={applySequenceLag}
        />
      ) : null}
    </div>
  );
}

function ProgrammeRowContextMenu({
  children,
  interactive,
  selectedCount,
  sequencePlans,
  sequenceLinkCount,
  onLink,
  onSetLag,
  onUnlink,
  onDelete,
}: {
  children: ReactElement;
  interactive: boolean;
  selectedCount: number;
  sequencePlans: ReadonlyMap<DependencyRelationshipCode, ProgrammeSequencePlan>;
  sequenceLinkCount: number;
  onLink: (code: DependencyRelationshipCode) => void;
  onSetLag: () => void;
  onUnlink: () => void;
  onDelete: () => void;
}) {
  if (!interactive) return children;
  const pairCount = Math.max(0, selectedCount - 1);
  const cycleBlocked = [...sequencePlans.values()].some((plan) => plan.wouldCycle);
  const limitBlocked = [...sequencePlans.values()].every((plan) => plan.exceedsLimit);

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent className="w-64">
        <ContextMenuLabel>
          {selectedCount} row{selectedCount === 1 ? "" : "s"} selected
        </ContextMenuLabel>
        <ContextMenuSeparator />
        <ContextMenuLabel className="flex items-center gap-2 py-1 text-[10px] uppercase tracking-[0.12em]">
          <Link2 className="size-3" aria-hidden />
          Link in sequence · {pairCount} link{pairCount === 1 ? "" : "s"}
        </ContextMenuLabel>
        {DEPENDENCY_RELATIONSHIPS.map((option) => {
          const plan = sequencePlans.get(option.code);
          return (
            <ContextMenuItem
              key={option.code}
              disabled={
                selectedCount < 2 ||
                cycleBlocked ||
                !plan ||
                plan.exceedsLimit
              }
              onSelect={() => onLink(option.code)}
            >
              <span className="w-6 font-mono text-[10px] font-semibold text-[var(--sw-text-primary)]">
                {option.code}
              </span>
              <span>{option.label}</span>
            </ContextMenuItem>
          );
        })}
        {cycleBlocked ? (
          <ContextMenuLabel className="py-1 text-[10px] leading-4 text-[var(--sw-warning)]">
            Linking these rows would create a cycle.
          </ContextMenuLabel>
        ) : limitBlocked ? (
          <ContextMenuLabel className="py-1 text-[10px] leading-4">
            This selection is too large to link at once.
          </ContextMenuLabel>
        ) : null}
        <ContextMenuSeparator />
        <ContextMenuItem disabled={sequenceLinkCount === 0} onSelect={onSetLag}>
          <Timer className="size-3.5" aria-hidden />
          Set lag on sequence…
        </ContextMenuItem>
        <ContextMenuItem disabled={sequenceLinkCount === 0} onSelect={onUnlink}>
          <Unlink className="size-3.5" aria-hidden />
          Unlink sequence
        </ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem variant="destructive" onSelect={onDelete}>
          <Trash className="size-3.5" aria-hidden />
          Delete selected rows…
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}

function GanttAxis({
  start,
  days,
  scale,
  leftPane,
  headerHeight,
  fitted,
  pxPerDay,
  showScheduleColumns,
  allStagesCollapsed,
  onToggleAllStages,
  selectedCount,
  onDeleteSelected,
}: {
  start: string;
  days: number;
  scale: ProgrammeScale;
  leftPane: number;
  headerHeight: number;
  fitted: boolean;
  pxPerDay: number;
  showScheduleColumns: boolean;
  allStagesCollapsed: boolean;
  onToggleAllStages?: () => void;
  selectedCount?: number;
  onDeleteSelected?: () => void;
}) {
  const end = addDays(start, days);
  const { major, minor } = programmeHeaderLayers(start, end, scale, pxPerDay);
  return (
    <div
      data-gantt-header=""
      className="program-gantt-header absolute inset-x-0 top-0 z-[1] border-b text-[10px] leading-none text-[var(--sw-text-tertiary)]"
      style={{ height: headerHeight }}
    >
      <div className="absolute bottom-1 left-1 flex items-center gap-0.5">
        {onToggleAllStages ? (
          <button
            type="button"
            aria-label={allStagesCollapsed ? "Expand all stages" : "Collapse all stages"}
            aria-expanded={!allStagesCollapsed}
            className="flex size-5 items-center justify-center rounded-sm text-[var(--sw-text-tertiary)] hover:bg-[color-mix(in_oklch,var(--sw-panel)_72%,transparent)] hover:text-[var(--sw-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sw-beam)]"
            onClick={onToggleAllStages}
          >
            {allStagesCollapsed ? (
              <ChevronRight className="size-3.5" aria-hidden />
            ) : (
              <ChevronDown className="size-3.5" aria-hidden />
            )}
          </button>
        ) : null}
        <span className="program-gantt-header-label">Activity</span>
      </div>
      {showScheduleColumns ? (
        <>
          <span
            className="program-gantt-header-label absolute bottom-1.5"
            style={{ left: NAME_WIDTH }}
          >
            Start
          </span>
          <span
            className="program-gantt-header-label absolute bottom-1.5 text-center"
            style={{ left: NAME_WIDTH + DATE_WIDTH, width: DURATION_WIDTH - 6 }}
          >
            Days
          </span>
          {(selectedCount ?? 0) > 1 && onDeleteSelected ? (
            <button
              type="button"
              aria-label={`Delete ${selectedCount} selected activities`}
              title={`Delete ${selectedCount} selected`}
              className="absolute bottom-1 inline-flex size-5 items-center justify-center rounded-sm text-muted-foreground/70 hover:bg-[var(--sw-error-bg)] hover:text-destructive"
              style={{
                left: NAME_WIDTH + DATE_WIDTH + DURATION_WIDTH + PLUS_WIDTH,
              }}
              onClick={onDeleteSelected}
            >
              <Trash className="size-3.5" aria-hidden />
            </button>
          ) : null}
        </>
      ) : null}
      <span
        className="pointer-events-none absolute border-b border-[color-mix(in_oklch,var(--sw-text-tertiary)_25%,transparent)]"
        style={{ left: leftPane, right: 0, top: 20 }}
      />
      {major.map((band) => (
        <AxisLabel
          key={`major-${band.start}`}
          band={band}
          start={start}
          days={days}
          leftPane={leftPane}
          fitted={fitted}
          pxPerDay={pxPerDay}
          top={5}
          align="left"
        />
      ))}
      {minor.map((band) => (
        <AxisLabel
          key={`minor-${band.start}`}
          band={band}
          start={start}
          days={days}
          leftPane={leftPane}
          fitted={fitted}
          pxPerDay={pxPerDay}
          top={26}
          align="center"
        />
      ))}
    </div>
  );
}

function AxisLabel({
  band,
  start,
  days,
  leftPane,
  fitted,
  pxPerDay,
  top,
  align,
}: {
  band: ProgrammeAxisBand;
  start: string;
  days: number;
  leftPane: number;
  fitted: boolean;
  pxPerDay: number;
  top: number;
  align: "left" | "center";
}) {
  const offset = daysBetween(start, band.start);
  return (
    <span
      className={cn(
        "absolute overflow-hidden whitespace-nowrap px-px",
        align === "center" ? "text-center" : "text-left",
      )}
      title={band.title ?? band.label}
      style={{
        top,
        ...chartBoxStyle(fitted, leftPane, offset, band.days, days, pxPerDay, 8),
      }}
    >
      {band.label}
    </span>
  );
}

function GanttGrid({
  start,
  days,
  scale,
  leftPane,
  headerHeight,
  fitted,
  pxPerDay,
  rowCount,
}: {
  start: string;
  days: number;
  scale: ProgrammeScale;
  leftPane: number;
  headerHeight: number;
  fitted: boolean;
  pxPerDay: number;
  rowCount: number;
}) {
  const end = addDays(start, days);
  const { major, minor } = programmeHeaderLayers(start, end, scale, pxPerDay);
  const height = headerHeight + ROW_HEIGHT * Math.max(rowCount, 1);
  const seen = new Set<string>();
  const lines: { key: string; offset: number; weight: "major" | "minor" }[] = [];
  for (const [weight, bands] of [
    ["major", major],
    ["minor", minor],
  ] as const) {
    for (const band of bands) {
      if (seen.has(band.start)) continue;
      const offset = daysBetween(start, band.start);
      if (offset <= 0 || offset >= days) continue;
      seen.add(band.start);
      lines.push({ key: `${weight}-${band.start}`, offset, weight });
    }
  }
  return (
    <div
      className="pointer-events-none absolute inset-x-0 top-0"
      data-gantt-grid=""
      style={{ height }}
    >
      {lines.map((line) => (
        <span
          key={line.key}
          data-gantt-grid-x={line.key}
          className={cn("absolute top-0 h-full w-px", line.weight === "major" ? GRID_MAJOR : GRID_MINOR)}
          style={{
            left: chartBoxStyle(fitted, leftPane, line.offset, 0, days, pxPerDay).left,
          }}
        />
      ))}
    </div>
  );
}

const GanttRow = memo(function GanttRow({
  activity,
  index,
  spanStart,
  spanDays,
  focused,
  selected,
  previewed,
  interactive,
  fitted,
  pxPerDay,
  leftPane,
  headerHeight,
  hideRowDelete,
  collapsed,
  dropPlacement,
  dragging,
  onRowClick,
  onContextMenu,
  onRename,
  onMove,
  onResize,
  onResizeStart,
  onPreview,
  onDelete,
  onAdd,
  onToggleCollapse,
  linkingActive,
  pendingAnchor,
  onChooseAnchor,
  onReorder,
  ...contextMenuTriggerProps
}: {
  activity: ProgrammeActivity;
  index: number;
  spanStart: string;
  spanDays: number;
  focused: boolean;
  selected: boolean;
  previewed: boolean;
  interactive: boolean;
  fitted: boolean;
  pxPerDay: number;
  leftPane: number;
  headerHeight: number;
  hideRowDelete: boolean;
  collapsed: boolean;
  dropPlacement: "before" | "after" | null;
  dragging: boolean;
  onRowClick?: (event: ReactMouseEvent) => void;
  onContextMenu?: (event: ReactMouseEvent) => void;
  onRename: (name: string) => void;
  onMove: (start: string) => void;
  onResize: (days: number) => void;
  onResizeStart: (start: string, days: number) => void;
  onPreview: (values: Record<string, unknown> | null) => void;
  onDelete: () => void;
  onAdd: () => void;
  onToggleCollapse: () => void;
  linkingActive: boolean;
  pendingAnchor: DependencyAnchor | null;
  onChooseAnchor: (endpoint: DependencyEndpoint) => void;
  onReorder: (event: ReactPointerEvent) => void;
}) {
  const [drag, setDrag] = useState<{
    kind: "move" | "resize" | "resize-start";
    delta: number;
  } | null>(null);
  const minDuration = activity.kind === "milestone" ? 0 : 1;
  const startDelta =
    !previewed && drag?.kind === "move"
      ? drag.delta
      : !previewed && drag?.kind === "resize-start"
        ? Math.min(drag.delta, activity.duration_days - minDuration)
        : 0;
  const offset = daysBetween(spanStart, activity.start_date) + startDelta;
  const duration = Math.max(
    activity.duration_days +
      (!previewed && drag?.kind === "resize"
        ? drag.delta
        : !previewed && drag?.kind === "resize-start"
          ? -startDelta
          : 0),
    minDuration,
  );
  const top = headerHeight + index * ROW_HEIGHT;
  function beginDrag(
    event: ReactPointerEvent,
    kind: "move" | "resize" | "resize-start",
  ) {
    if (!interactive) return;
    event.preventDefault();
    event.stopPropagation();
    const originX = event.clientX;
    let previewFrame: number | null = null;
    let previewDelta = 0;
    let lastDelta: number | null = null;
    const previewValues = (delta: number): Record<string, unknown> => {
      if (kind === "move") return { start_date: addDays(activity.start_date, delta) };
      if (kind === "resize-start") {
        const bounded = Math.min(delta, activity.duration_days - minDuration);
        return {
          start_date: addDays(activity.start_date, bounded),
          duration_days: activity.duration_days - bounded,
        };
      }
      return { duration_days: Math.max(minDuration, activity.duration_days + delta) };
    };
    event.currentTarget.setPointerCapture?.(event.pointerId);
    const onMovePointer = (moveEvent: PointerEvent) => {
      const nextDelta = Math.round(
        (moveEvent.clientX - originX) / Math.max(pxPerDay, 0.25),
      );
      if (nextDelta === lastDelta) return;
      lastDelta = nextDelta;
      previewDelta = nextDelta;
      setDrag({ kind, delta: previewDelta });
      if (previewFrame === null) {
        previewFrame = window.requestAnimationFrame(() => {
          previewFrame = null;
          onPreview(previewValues(previewDelta));
        });
      }
    };
    const onUp = (upEvent: PointerEvent) => {
      window.removeEventListener("pointermove", onMovePointer);
      window.removeEventListener("pointerup", onUp);
      if (previewFrame !== null) window.cancelAnimationFrame(previewFrame);
      onPreview(null);
      const raw = Math.round((upEvent.clientX - originX) / Math.max(pxPerDay, 0.25));
      setDrag(null);
      if (raw === 0) return;
      if (kind === "move") {
        onMove(addDays(activity.start_date, raw));
        return;
      }
      if (kind === "resize-start") {
        const delta = Math.min(raw, activity.duration_days - minDuration);
        if (delta === 0) return;
        onResizeStart(addDays(activity.start_date, delta), activity.duration_days - delta);
        return;
      }
      onResize(Math.max(minDuration, activity.duration_days + raw));
    };
    window.addEventListener("pointermove", onMovePointer);
    window.addEventListener("pointerup", onUp);
  }

  return (
    <div
      {...contextMenuTriggerProps}
      className={cn(
        "group/row absolute inset-x-0 select-none border-b",
        GRID_ROW,
        (selected || focused) && "bg-[color-mix(in_oklch,var(--sw-beam)_8%,transparent)]",
        selected && "bg-[color-mix(in_oklch,var(--sw-beam)_14%,transparent)]",
        dragging && "opacity-60",
      )}
      style={{ top, height: ROW_HEIGHT }}
      data-activity-key={activity.activity_key}
      role="row"
      tabIndex={interactive ? 0 : undefined}
      aria-selected={selected}
      onClick={onRowClick}
      onContextMenu={onContextMenu}
      onKeyDown={(event) => {
        if (event.key !== "ContextMenu" && !(event.shiftKey && event.key === "F10")) {
          return;
        }
        event.preventDefault();
        const bounds = event.currentTarget.getBoundingClientRect();
        event.currentTarget.dispatchEvent(
          new MouseEvent("contextmenu", {
            bubbles: true,
            clientX: bounds.left + 12,
            clientY: bounds.top + ROW_HEIGHT / 2,
          }),
        );
      }}
    >
      {dropPlacement ? (
        <span
          className="absolute inset-x-0 z-10 h-0.5 bg-[var(--sw-beam)]"
          style={{ top: dropPlacement === "before" ? 0 : ROW_HEIGHT - 2 }}
        />
      ) : null}
      {interactive ? (
        <RowFields
          activity={activity}
          onRename={onRename}
          onMove={onMove}
          onResize={onResize}
          onDelete={onDelete}
          onAdd={onAdd}
          collapsed={collapsed}
          onToggleCollapse={onToggleCollapse}
          onReorder={onReorder}
          hideDelete={hideRowDelete}
        />
      ) : (
        <FigureFields activity={activity} />
      )}
      <div
        className={cn(
          "absolute overflow-visible",
          activity.kind === "activity" && "program-gantt-activity-bar",
        )}
        data-gantt-bar={activity.activity_key}
        style={{
          ...milestoneBoxStyle(
            activity.kind === "milestone",
            chartBoxStyle(fitted, leftPane, offset, duration, spanDays, pxPerDay, 8),
          ),
          top: BAR_TOP,
          height: BAR_HEIGHT,
        }}
      >
        {activity.kind === "stage" ? (
          <>
            <span
              aria-hidden
              data-gantt-summary=""
              className="program-gantt-summary-bar pointer-events-none absolute inset-x-0 top-1.5 h-[3px]"
            />
            <span
              aria-hidden
              data-gantt-endpoint-stroke="start"
              data-gantt-endpoint-active={linkingActive ? "true" : "false"}
              data-gantt-endpoint-selected={
                pendingAnchor?.activityKey === activity.activity_key &&
                pendingAnchor.endpoint === "start"
                  ? "true"
                  : "false"
              }
              className="program-gantt-summary-bar program-gantt-endpoint-stroke pointer-events-none absolute top-1.5 left-0 h-2.5 w-[3px]"
            />
            <span
              aria-hidden
              data-gantt-endpoint-stroke="finish"
              data-gantt-endpoint-active={linkingActive ? "true" : "false"}
              data-gantt-endpoint-selected={
                pendingAnchor?.activityKey === activity.activity_key &&
                pendingAnchor.endpoint === "finish"
                  ? "true"
                  : "false"
              }
              className="program-gantt-summary-bar program-gantt-endpoint-stroke pointer-events-none absolute top-1.5 right-0 h-2.5 w-[3px]"
            />
            {interactive ? (
              <button
                type="button"
                aria-label={`Move ${activity.name}`}
                className="absolute inset-0 block h-full w-full bg-transparent p-0 leading-none"
                onPointerDown={(event) => beginDrag(event, "move")}
                data-interactive="true"
              />
            ) : null}
          </>
        ) : activity.kind === "milestone" ? (
          interactive ? (
            <button
              type="button"
              aria-label={`Move ${activity.name}`}
              className="absolute top-1/2 left-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rotate-45 bg-[var(--sw-beam)] p-0 leading-none"
              onPointerDown={(event) => beginDrag(event, "move")}
              data-interactive="true"
            />
          ) : (
            <span className="absolute top-1/2 left-1/2 block size-2.5 -translate-x-1/2 -translate-y-1/2 rotate-45 bg-[var(--sw-beam)]" aria-hidden />
          )
        ) : interactive ? (
          <button
            type="button"
            aria-label={`Move ${activity.name}`}
            className="block h-full w-full bg-transparent p-0 leading-none"
            onPointerDown={(event) => beginDrag(event, "move")}
            data-interactive="true"
          />
        ) : (
          <span className="block h-full w-full" aria-hidden />
        )}
        {interactive && activity.kind !== "milestone" ? (
          <>
            {activity.kind === "activity" ? (
              <>
                <span
                  aria-hidden
                  data-gantt-handle="start"
                  data-gantt-endpoint-stroke="start"
                  data-gantt-endpoint-active={linkingActive ? "true" : "false"}
                  data-gantt-endpoint-selected={
                    pendingAnchor?.activityKey === activity.activity_key &&
                    pendingAnchor.endpoint === "start"
                      ? "true"
                      : "false"
                  }
                  className="program-gantt-endpoint-stroke pointer-events-none absolute top-1/2 left-1 h-2.5 w-0.5 -translate-y-1/2 rounded-sm"
                />
                <span
                  aria-hidden
                  data-gantt-handle="end"
                  data-gantt-endpoint-stroke="finish"
                  data-gantt-endpoint-active={linkingActive ? "true" : "false"}
                  data-gantt-endpoint-selected={
                    pendingAnchor?.activityKey === activity.activity_key &&
                    pendingAnchor.endpoint === "finish"
                      ? "true"
                      : "false"
                  }
                  className="program-gantt-endpoint-stroke pointer-events-none absolute top-1/2 right-1 h-2.5 w-0.5 -translate-y-1/2 rounded-sm"
                />
              </>
            ) : null}
            <span
              role="separator"
              aria-label={`Resize start of ${activity.name}`}
              data-interactive="true"
              className="absolute inset-y-0 left-0 z-10 w-2.5 cursor-ew-resize"
              onPointerDown={(event) => beginDrag(event, "resize-start")}
            />
            <span
              role="separator"
              aria-label={`Resize ${activity.name}`}
              data-interactive="true"
              className="absolute inset-y-0 right-0 z-10 w-2.5 cursor-ew-resize"
              onPointerDown={(event) => beginDrag(event, "resize")}
            />
          </>
        ) : null}
        {interactive ? (
          <DependencyAnchors
            activity={activity}
            active={linkingActive}
            pendingAnchor={pendingAnchor}
            onChoose={onChooseAnchor}
          />
        ) : null}
      </div>
    </div>
  );
});

function DependencyAnchors({
  activity,
  active,
  pendingAnchor,
  onChoose,
}: {
  activity: ProgrammeActivity;
  active: boolean;
  pendingAnchor: DependencyAnchor | null;
  onChoose: (endpoint: DependencyEndpoint) => void;
}) {
  return (
    <>
      {(["start", "finish"] as const).map((endpoint) => {
        const selected =
          pendingAnchor?.activityKey === activity.activity_key &&
          pendingAnchor.endpoint === endpoint;
        return (
          <button
            key={endpoint}
            type="button"
            tabIndex={active ? 0 : -1}
            aria-label={`Choose ${endpoint} of ${activity.name} for dependency`}
            data-gantt-anchor={endpoint}
            data-gantt-anchor-active={active ? "true" : "false"}
            className={cn(
              "program-gantt-dependency-anchor absolute inset-y-0 z-20 w-3 bg-transparent p-0 opacity-0 focus-visible:opacity-100 focus-visible:outline-1 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--sw-text-primary)]",
              endpoint === "start" ? "-left-1.5" : "-right-1.5",
              active ? "pointer-events-auto cursor-crosshair" : "pointer-events-none",
              selected && "focus-visible:outline-2",
            )}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              if (active) onChoose(endpoint);
            }}
          />
        );
      })}
    </>
  );
}

function GanttLinks({
  activities,
  dependencies,
  spanStart,
  spanDays,
  fitted,
  pxPerDay,
  leftPane,
  headerHeight,
  interactive,
  linkingActive,
  selectedDependencyKey,
  onSelectDependency,
}: {
  activities: ProgrammeActivity[];
  dependencies: ProgrammeDependency[];
  spanStart: string;
  spanDays: number;
  fitted: boolean;
  pxPerDay: number;
  leftPane: number;
  headerHeight: number;
  interactive: boolean;
  linkingActive: boolean;
  selectedDependencyKey: string | null;
  onSelectDependency: (dependencyKey: string | null) => void;
}) {
  const height = ROW_HEIGHT * Math.max(activities.length, 1);
  const width = fitted ? undefined : Math.max(spanDays * pxPerDay, 8);
  const links = programmeLinks(activities, dependencies, spanStart);
  if (!links.length) return null;
  const xScale = fitted ? 1 : pxPerDay;
  const stubX = fitted ? Math.max(2, spanDays * 0.012) : 8;
  return (
    <svg
      className="pointer-events-none absolute z-20"
      data-gantt-links=""
      style={{
        left: leftPane,
        top: headerHeight,
        width: fitted ? `calc(100% - ${leftPane}px)` : width,
        height,
      }}
      viewBox={fitted ? `0 0 ${spanDays} ${height}` : undefined}
      preserveAspectRatio={fitted ? "none" : undefined}
    >
      <defs>
        <marker
          id="programme-dependency-arrow"
          viewBox="0 0 6 6"
          refX="5"
          refY="3"
          markerWidth="5"
          markerHeight="5"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 6 3 L 0 6 Z" fill="var(--sw-beam)" />
        </marker>
        <marker
          id="programme-dependency-arrow-illuminated"
          viewBox="0 0 6 6"
          refX="5"
          refY="3"
          markerWidth="5"
          markerHeight="5"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 6 3 L 0 6 Z" fill="var(--sw-text-primary)" />
        </marker>
      </defs>
      {links.map((link) => {
        const illuminated = linkingActive || selectedDependencyKey === link.key;
        return (
          <g
            key={link.key}
            data-gantt-link-illuminated={illuminated ? "true" : "false"}
          >
            {interactive ? (
              <path
                data-gantt-link-hit={link.key}
                d={ganttLinkPath(link, ROW_HEIGHT, LINK_Y, xScale, stubX)}
                fill="none"
                stroke="transparent"
                strokeWidth="12"
                vectorEffect="non-scaling-stroke"
                pointerEvents="stroke"
                className="pointer-events-auto cursor-pointer"
                onClick={(event) => {
                  event.stopPropagation();
                  onSelectDependency(link.key);
                }}
              />
            ) : null}
            <path
              data-gantt-link={link.key}
              d={ganttLinkPath(link, ROW_HEIGHT, LINK_Y, xScale, stubX)}
              fill="none"
              stroke={illuminated ? "var(--sw-text-primary)" : "var(--sw-beam)"}
              strokeOpacity={illuminated ? "1" : "0.55"}
              strokeWidth={
                selectedDependencyKey === link.key ? "2" : illuminated ? "1.75" : "1.25"
              }
              markerEnd={
                illuminated
                  ? "url(#programme-dependency-arrow-illuminated)"
                  : "url(#programme-dependency-arrow)"
              }
              vectorEffect="non-scaling-stroke"
              pointerEvents="none"
              className="transition-[stroke,stroke-opacity] duration-100"
            />
            {link.lagDays > 0 ? (
              <text
                x={((link.fromOffset + link.toOffset) / 2) * xScale}
                y={((link.fromIndex + link.toIndex) / 2) * ROW_HEIGHT + LINK_Y - 3}
                textAnchor="middle"
                fill={illuminated ? "var(--sw-text-primary)" : "var(--sw-beam)"}
                stroke="var(--sw-void)"
                strokeWidth="3"
                paintOrder="stroke"
                fontSize="9"
                fontFamily="ui-monospace, monospace"
                pointerEvents="none"
                vectorEffect="non-scaling-stroke"
              >
                +{link.lagDays}d
              </text>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
}

function DependencyEditor({
  dependency,
  activities,
  spanStart,
  spanDays,
  fitted,
  pxPerDay,
  leftPane,
  headerHeight,
  onChangeRelationship,
  onChangeLag,
  onRemove,
  onClose,
}: {
  dependency: ProgrammeDependency | undefined;
  activities: ProgrammeActivity[];
  spanStart: string;
  spanDays: number;
  fitted: boolean;
  pxPerDay: number;
  leftPane: number;
  headerHeight: number;
  onChangeRelationship: (
    dependency: ProgrammeDependency,
    sourceEndpoint: DependencyEndpoint,
    targetEndpoint: DependencyEndpoint,
  ) => void;
  onChangeLag: (dependency: ProgrammeDependency, lagDays: number) => void;
  onRemove: (dependency: ProgrammeDependency) => void;
  onClose: () => void;
}) {
  const [lagDraft, setLagDraft] = useState(dependency?.lag_days ?? 0);
  if (!dependency) return null;
  const sourceIndex = activities.findIndex(
    (item) => item.activity_key === dependency.source_activity_key,
  );
  const targetIndex = activities.findIndex(
    (item) => item.activity_key === dependency.target_activity_key,
  );
  const source = activities[sourceIndex];
  const target = activities[targetIndex];
  if (!source || !target) return null;
  const sourceSpan = programmeActivitySpan(spanStart, source);
  const targetSpan = programmeActivitySpan(spanStart, target);
  const sourceOffset =
    dependency.source_endpoint === "start" ? sourceSpan.start : sourceSpan.end;
  const targetOffset =
    dependency.target_endpoint === "start" ? targetSpan.start : targetSpan.end;
  const midpoint = (sourceOffset + targetOffset) / 2;
  const position = chartBoxStyle(
    fitted,
    leftPane,
    midpoint,
    0,
    spanDays,
    pxPerDay,
  );
  const unclampedLeft =
    typeof position.left === "number" ? `${position.left}px` : position.left;
  const editorLeft = `clamp(${DEPENDENCY_EDITOR_HALF_WIDTH}px, ${unclampedLeft}, calc(100% - ${DEPENDENCY_EDITOR_HALF_WIDTH}px))`;
  const relationship = `${dependency.source_endpoint[0]?.toUpperCase()}${dependency.target_endpoint[0]?.toUpperCase()}`;
  function commitLag() {
    const next = Math.max(0, Number.isFinite(lagDraft) ? lagDraft : 0);
    setLagDraft(next);
    if (next !== dependency!.lag_days) onChangeLag(dependency!, next);
  }
  return (
    <div
      role="dialog"
      aria-label={`Edit ${relationship} dependency`}
      className="program-gantt-dependency-editor absolute z-30 w-48 rounded-md border p-2.5 shadow-md"
      style={{
        left: editorLeft,
        top: headerHeight + ((sourceIndex + targetIndex) / 2) * ROW_HEIGHT + ROW_HEIGHT / 2,
        transform: "translate(-50%, 6px)",
      }}
      onClick={(event) => event.stopPropagation()}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-[11px] font-medium text-[var(--sw-text-primary)]">
          Dependency
        </span>
        <Button
          type="button"
          size="icon-xs"
          variant="ghost"
          aria-label="Close dependency editor"
          className="rounded-sm text-[var(--sw-text-tertiary)] hover:bg-[color-mix(in_oklch,var(--sw-void)_65%,transparent)] hover:text-[var(--sw-text-primary)]"
          onClick={onClose}
        >
          <X className="size-3" aria-hidden />
        </Button>
      </div>
      <div
        role="group"
        aria-label="Dependency type"
        className="program-gantt-dependency-types grid grid-cols-4 overflow-hidden rounded-sm"
      >
        {DEPENDENCY_RELATIONSHIPS.map((option) => {
          const selected = relationship === option.code;
          return (
            <button
              key={option.code}
              type="button"
              aria-label={`${option.label} (${option.code})`}
              aria-pressed={selected}
              title={option.label}
              className="program-gantt-dependency-type h-7 font-mono text-[10px] font-medium"
              onClick={() =>
                onChangeRelationship(
                  dependency,
                  option.sourceEndpoint,
                  option.targetEndpoint,
                )
              }
            >
              {option.code}
            </button>
          );
        })}
      </div>
      <label className="mt-2.5 flex items-center gap-2 text-[10px] text-[var(--sw-text-secondary)]">
        <span>Lag</span>
        <Input
          type="number"
          min={0}
          value={lagDraft}
          aria-label="Dependency lag in days"
          className="program-gantt-dependency-lag h-7 min-w-0 flex-1 rounded-sm px-1 text-center text-[10px]"
          onChange={(event) => setLagDraft(Math.max(0, Number(event.target.value)))}
          onBlur={commitLag}
          onKeyDown={(event) => {
            if (event.key === "Enter") commitLag();
          }}
        />
        <span>days</span>
      </label>
      <div className="mt-2 flex items-center justify-between gap-2 border-t border-[var(--sw-edge)] pt-2">
        <Button
          type="button"
          size="xs"
          variant="ghost"
          className="h-6 rounded-sm px-1.5 text-[10px] font-normal text-[var(--sw-beam)] hover:bg-[color-mix(in_oklch,var(--sw-beam)_10%,transparent)] hover:text-[var(--sw-text-primary)]"
          onClick={() => {
            setLagDraft(0);
            onChangeLag(dependency, 0);
          }}
        >
          Reset to ASAP
        </Button>
        <Button
          type="button"
          size="icon-xs"
          variant="ghost"
          aria-label="Remove dependency"
          title="Remove dependency"
          className="rounded-sm text-muted-foreground/70 hover:bg-[var(--sw-error-bg)] hover:text-destructive"
          onClick={() => onRemove(dependency)}
        >
          <Trash className="size-3.5" aria-hidden />
        </Button>
      </div>
    </div>
  );
}

function FigureFields({ activity }: { activity: ProgrammeActivity }) {
  return (
    <>
      <span
        className={cn(
          "absolute left-0 truncate px-2 text-left",
          ROW_TEXT,
          activity.kind === "stage" ? "font-semibold" : "pl-5 text-[var(--sw-text-secondary)]",
        )}
        style={{ width: NAME_WIDTH, top: 4 }}
      >
        {activity.name}
      </span>
      <span
        className={cn("absolute truncate text-left", ROW_TEXT)}
        style={{ left: NAME_WIDTH, width: DATE_WIDTH - 4, top: 4 }}
      >
        {formatCompactDate(activity.start_date)}
      </span>
      <span
        className={cn("absolute text-center tabular-nums", ROW_TEXT)}
        style={{ left: NAME_WIDTH + DATE_WIDTH, width: DURATION_WIDTH - 6, top: 4 }}
      >
        {activity.duration_days}
      </span>
    </>
  );
}

function RowFields({
  activity,
  onRename,
  onMove,
  onResize,
  onDelete,
  onAdd,
  collapsed,
  onToggleCollapse,
  onReorder,
  hideDelete,
}: {
  activity: ProgrammeActivity;
  onRename: (name: string) => void;
  onMove: (start: string) => void;
  onResize: (days: number) => void;
  onDelete: () => void;
  onAdd: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  onReorder: (event: ReactPointerEvent) => void;
  hideDelete: boolean;
}) {
  const [editingName, setEditingName] = useState(false);
  const [draftName, setDraftName] = useState(activity.name);
  const [durationDraft, setDurationDraft] = useState(activity.duration_days);
  const [durationEditing, setDurationEditing] = useState(false);

  function commitName() {
    const next = draftName.trim();
    setEditingName(false);
    if (next && next !== activity.name) onRename(next);
    else setDraftName(activity.name);
  }

  const nameLeft = GRIP_WIDTH + (activity.kind === "stage" ? 20 : 12);
  const actionsLeft = NAME_WIDTH + DATE_WIDTH + DURATION_WIDTH;

  return (
    <>
      <button
        type="button"
        aria-label={`Reorder ${activity.name}`}
        className="absolute top-0.5 flex h-5 w-4 cursor-grab items-center justify-center text-[var(--sw-text-tertiary)] opacity-0 hover:text-[var(--sw-text-primary)] active:cursor-grabbing group-hover/row:opacity-100 group-focus-within/row:opacity-100"
        style={{ left: 2 }}
        onPointerDown={onReorder}
      >
        <GripVertical className="size-3.5" aria-hidden />
      </button>
      {activity.kind === "stage" ? (
        <button
          type="button"
          aria-label={collapsed ? `Expand ${activity.name}` : `Collapse ${activity.name}`}
          aria-expanded={!collapsed}
          className="absolute top-0.5 inline-flex size-5 items-center justify-center rounded-sm text-[var(--sw-text-tertiary)] hover:bg-[color-mix(in_oklch,var(--sw-panel)_72%,transparent)] hover:text-[var(--sw-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sw-beam)]"
          style={{ left: GRIP_WIDTH }}
          onClick={(event) => {
            event.stopPropagation();
            onToggleCollapse();
          }}
        >
          {collapsed ? (
            <ChevronRight className="size-3.5" aria-hidden />
          ) : (
            <ChevronDown className="size-3.5" aria-hidden />
          )}
        </button>
      ) : null}
      {editingName ? (
        <Input
          autoFocus
          value={draftName}
          aria-label={`${activity.kind} name`}
          className={cn("program-gantt-field absolute top-0.5 h-5 px-1.5", ROW_TEXT)}
          style={{ left: nameLeft, width: NAME_WIDTH - nameLeft - 4 }}
          onChange={(event) => setDraftName(event.target.value)}
          onBlur={commitName}
          onKeyDown={(event) => {
            if (event.key === "Enter") commitName();
            if (event.key === "Escape") {
              setDraftName(activity.name);
              setEditingName(false);
            }
          }}
        />
      ) : (
        <button
          type="button"
          className={cn(
            "absolute top-0.5 truncate px-1.5 text-left",
            ROW_TEXT,
            activity.kind === "stage" ? "font-semibold" : "text-[var(--sw-text-secondary)]",
          )}
          style={{ left: nameLeft, width: NAME_WIDTH - nameLeft - 4 }}
          onClick={(event) => {
            if (event.shiftKey || event.ctrlKey || event.metaKey) return;
            event.stopPropagation();
            setDraftName(activity.name);
            setEditingName(true);
          }}
        >
          {activity.name}
        </button>
      )}
      <div className="absolute top-0.5" style={{ left: NAME_WIDTH, width: DATE_WIDTH - 4 }}>
        <ProgrammeDateField
          value={activity.start_date}
          ariaLabel={`${activity.name} start date`}
          onChange={onMove}
        />
      </div>
      <Input
        type="number"
        min={activity.kind === "milestone" ? 0 : 1}
        value={durationEditing ? durationDraft : activity.duration_days}
        aria-label={`${activity.name} duration in days`}
        className={cn(
          "program-gantt-field absolute top-0.5 h-5 px-0.5 text-center",
          ROW_TEXT,
        )}
        style={{ left: NAME_WIDTH + DATE_WIDTH, width: DURATION_WIDTH - 6 }}
        onFocus={() => {
          setDurationEditing(true);
          setDurationDraft(activity.duration_days);
        }}
        onBlur={() => {
          setDurationEditing(false);
          setDurationDraft(activity.duration_days);
        }}
        onChange={(event) => {
          const days = Math.max(
            activity.kind === "milestone" ? 0 : 1,
            Number(event.target.value),
          );
          setDurationDraft(days);
          onResize(days);
        }}
      />
      <button
        type="button"
        aria-label={
          activity.kind === "stage"
            ? `Add parent group after ${activity.name}`
            : `Add activity after ${activity.name}`
        }
        title={activity.kind === "stage" ? "Add parent group" : "Add activity"}
        className="absolute top-0.5 inline-flex size-5 items-center justify-center rounded-sm text-muted-foreground/70 opacity-70 hover:bg-[color-mix(in_oklch,var(--sw-panel)_72%,transparent)] hover:text-[var(--sw-text-primary)] hover:opacity-100 focus-visible:opacity-100"
        style={{ left: actionsLeft }}
        onClick={(event) => {
          event.stopPropagation();
          onAdd();
        }}
      >
        <Plus className="size-3.5" aria-hidden />
      </button>
      {hideDelete ? null : (
        <button
          type="button"
          aria-label={`Delete ${activity.name}`}
          title="Delete"
          className="absolute top-0.5 inline-flex size-5 items-center justify-center rounded-sm text-muted-foreground/70 opacity-0 transition-opacity hover:bg-[var(--sw-error-bg)] hover:text-destructive group-hover/row:opacity-100 group-focus-within/row:opacity-100"
          style={{ left: actionsLeft + PLUS_WIDTH }}
          onClick={(event) => {
            event.stopPropagation();
            onDelete();
          }}
        >
          <Trash className="size-3.5" aria-hidden />
        </button>
      )}
    </>
  );
}
