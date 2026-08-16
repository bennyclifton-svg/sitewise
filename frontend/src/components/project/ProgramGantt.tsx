import {
  memo,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { GripVertical, Link2, Plus, Trash, Unlink } from "lucide-react";

import { ProgrammeDateField } from "@/components/project/ProgrammeDateField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  addDays,
  daysBetween,
  previousProgrammeKey,
  programmeBulkDeleteOperations,
  programmeLinkWouldCycle,
  programmeRowMove,
  programmeScaleBands,
  programmeSpan,
  programmeWeekTicks,
  type ProgrammeActivity,
  type ProgrammeAxisBand,
  type ProgrammeOperation,
  type ProgrammeScale,
  type ProgrammeState,
} from "@/lib/programme";
import { cn } from "@/lib/utils";

const ROW_HEIGHT = 32;
const NAME_WIDTH = 168;
const DATE_WIDTH = 128;
const DURATION_WIDTH = 76;
const LINK_WIDTH = 24;
const PLUS_WIDTH = 24;
const TRASH_WIDTH = 24;
const GRIP_WIDTH = 18;
const SCALE_PX: Record<ProgrammeScale, number> = {
  week: 18,
  month: 6,
  quarter: 2,
};

export function ProgramGantt({
  state,
  mode,
  onOperate,
  onScaleChange,
  onOpenProgram,
}: {
  state: ProgrammeState;
  mode: "edit" | "figure";
  onOperate?: (operations: ProgrammeOperation[]) => void;
  onScaleChange?: (scale: ProgrammeScale) => void;
  onOpenProgram?: () => void;
}) {
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const [surfaceWidth, setSurfaceWidth] = useState(0);
  const [fitToScreen, setFitToScreen] = useState(false);
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [selectionAnchor, setSelectionAnchor] = useState<string | null>(null);
  const [rowDrag, setRowDrag] = useState<{
    key: string;
    overKey: string;
    placement: "before" | "after";
  } | null>(null);
  const activityKeys = useMemo(
    () => new Set(state.activities.map((item) => item.activity_key)),
    [state.activities],
  );
  const visibleSelected = useMemo(() => {
    const next = new Set([...selectedKeys].filter((key) => activityKeys.has(key)));
    return next.size === selectedKeys.size ? selectedKeys : next;
  }, [selectedKeys, activityKeys]);
  const visibleAnchor =
    selectionAnchor && activityKeys.has(selectionAnchor) ? selectionAnchor : null;
  const span = useMemo(() => programmeSpan(state.activities), [state.activities]);
  const spanDays = Math.max(daysBetween(span.start, span.end), 1);
  const fitted = mode === "figure" || fitToScreen;
  const leftPane =
    mode === "figure"
      ? NAME_WIDTH
      : NAME_WIDTH +
        DATE_WIDTH +
        DURATION_WIDTH +
        LINK_WIDTH +
        PLUS_WIDTH +
        TRASH_WIDTH;
  const headerHeight = state.view_scale === "week" ? 44 : 28;
  const measuredChart = Math.max((surfaceWidth || 720) - leftPane, 80);
  const pxPerDay = fitted ? measuredChart / spanDays : SCALE_PX[state.view_scale];
  const chartWidth = fitted ? measuredChart : Math.max(spanDays * pxPerDay, 320);

  useEffect(() => {
    const node = surfaceRef.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width ?? 0;
      setSurfaceWidth(width);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (visibleSelected.size === 0) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelectedKeys(new Set());
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visibleSelected.size]);

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
    const keys = state.activities.map((item) => item.activity_key);
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

  function addActivityBelow(row: ProgrammeActivity) {
    const parent = row.kind === "stage" ? row.activity_key : row.parent_key;
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

  function addStage() {
    const last =
      [...state.activities].reverse().find((item) => item.kind === "stage") ??
      state.activities.at(-1);
    onOperate?.([
      {
        operation: "ADD",
        target_type: "stage",
        reference_id: last?.activity_key,
        placement: "after",
        values: {
          name: "New stage",
          start_date: last?.finish_date || span.end,
          duration_days: 30,
        },
      },
    ]);
  }

  function toggleLink(row: ProgrammeActivity) {
    if (row.predecessor_key) {
      update(row, { predecessor_key: null, lag_days: 0 });
      return;
    }
    const predecessor = previousProgrammeKey(state.activities, row.activity_key);
    if (!predecessor || programmeLinkWouldCycle(state.activities, row.activity_key, predecessor)) {
      return;
    }
    update(row, { predecessor_key: predecessor, lag_days: 0 });
  }

  function beginRowDrag(event: ReactPointerEvent, sourceKey: string) {
    event.preventDefault();
    event.stopPropagation();
    const surface = surfaceRef.current;
    if (!surface) return;
    const readTarget = (clientY: number) => {
      const top = surface.getBoundingClientRect().top + headerHeight;
      const raw = (clientY - top) / ROW_HEIGHT;
      const index = Math.max(0, Math.min(state.activities.length - 1, Math.floor(raw)));
      return {
        overKey: state.activities[index]?.activity_key ?? sourceKey,
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
          height: headerHeight + ROW_HEIGHT * Math.max(state.activities.length, 1),
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
          showScheduleColumns={mode === "edit"}
          onAddStage={mode === "edit" ? addStage : undefined}
          selectedCount={mode === "edit" ? visibleSelected.size : 0}
          onDeleteSelected={mode === "edit" ? removeSelected : undefined}
        />
        <GanttLinks
          activities={state.activities}
          spanStart={span.start}
          spanDays={spanDays}
          fitted={fitted}
          pxPerDay={pxPerDay}
          leftPane={leftPane}
          headerHeight={headerHeight}
        />
        {state.activities.map((activity, index) => (
          <GanttRow
            key={activity.activity_key}
            activity={activity}
            index={index}
            spanStart={span.start}
            spanDays={spanDays}
            focused={focusKey === activity.activity_key}
            selected={visibleSelected.has(activity.activity_key)}
            interactive={mode === "edit"}
            fitted={fitted}
            pxPerDay={pxPerDay}
            headerHeight={headerHeight}
            hideRowDelete={visibleSelected.size > 1}
            onRowClick={(event) => handleRowClick(event, activity.activity_key)}
            dropPlacement={
              rowDrag?.overKey === activity.activity_key ? rowDrag.placement : null
            }
            dragging={rowDrag?.key === activity.activity_key}
            onRename={(name) => update(activity, { name })}
            onMove={(start) => update(activity, { start_date: start })}
            onResize={(days) => update(activity, { duration_days: days })}
            onDelete={() => remove(activity)}
            onAddActivity={() => addActivityBelow(activity)}
            onToggleLink={() => toggleLink(activity)}
            onReorder={(event) => beginRowDrag(event, activity.activity_key)}
          />
        ))}
      </div>
    </div>
  );

  if (mode === "figure") {
    return (
      <button
        type="button"
        className="block w-full text-left"
        onClick={onOpenProgram}
        aria-label="Open Program"
      >
        {chart}
      </button>
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
              variant={state.view_scale === scale && !fitToScreen ? "default" : "ghost"}
              className="rounded-none capitalize"
              onClick={() => {
                setFitToScreen(false);
                onScaleChange?.(scale);
              }}
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
    </div>
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
  onAddStage,
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
  onAddStage?: () => void;
  selectedCount?: number;
  onDeleteSelected?: () => void;
}) {
  const end = addDays(start, days);
  const bands = programmeScaleBands(start, end, scale);
  const weekTicks = scale === "week" ? programmeWeekTicks(start, end) : [];
  return (
    <div
      className="absolute inset-x-0 top-0 border-b text-[10px] text-[var(--sw-text-tertiary)]"
      style={{ height: headerHeight }}
    >
      <span className="absolute left-2 top-2">Activity</span>
      {onAddStage ? (
        <button
          type="button"
          aria-label="Add stage"
          className="absolute top-1 flex size-5 items-center justify-center text-[var(--sw-text-tertiary)] hover:text-[var(--sw-text-primary)]"
          style={{ left: 54 }}
          onClick={onAddStage}
        >
          <Plus className="size-3.5" aria-hidden />
        </button>
      ) : null}
      {showScheduleColumns ? (
        <>
          <span className="absolute top-2" style={{ left: NAME_WIDTH }}>
            Start
          </span>
          <span className="absolute top-2" style={{ left: NAME_WIDTH + DATE_WIDTH }}>
            Days
          </span>
          {(selectedCount ?? 0) > 1 && onDeleteSelected ? (
            <button
              type="button"
              aria-label={`Delete ${selectedCount} selected activities`}
              title={`Delete ${selectedCount} selected`}
              className="absolute top-1 inline-flex size-5 items-center justify-center rounded-sm text-muted-foreground/70 hover:bg-destructive/10 hover:text-destructive"
              style={{
                left: NAME_WIDTH + DATE_WIDTH + DURATION_WIDTH + LINK_WIDTH + PLUS_WIDTH,
              }}
              onClick={onDeleteSelected}
            >
              <Trash className="size-3.5" aria-hidden />
            </button>
          ) : null}
        </>
      ) : null}
      {bands.map((band) => (
        <AxisLabel
          key={`band-${band.start}`}
          band={band}
          start={start}
          days={days}
          leftPane={leftPane}
          fitted={fitted}
          pxPerDay={pxPerDay}
          top={scale === "week" ? 4 : 8}
        />
      ))}
      {weekTicks.map((tick) => (
        <AxisLabel
          key={`tick-${tick.start}`}
          band={tick}
          start={start}
          days={days}
          leftPane={leftPane}
          fitted={fitted}
          pxPerDay={pxPerDay}
          top={24}
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
}: {
  band: ProgrammeAxisBand;
  start: string;
  days: number;
  leftPane: number;
  fitted: boolean;
  pxPerDay: number;
  top: number;
}) {
  const offset = daysBetween(start, band.start);
  return (
    <span
      className="absolute truncate"
      style={{
        top,
        left: fitted
          ? `calc(${leftPane}px + ${(offset * 100) / days}%)`
          : leftPane + offset * pxPerDay,
        maxWidth: fitted
          ? `calc(${(band.days * 100) / days}%)`
          : Math.max(band.days * pxPerDay - 4, 36),
      }}
    >
      {band.label}
    </span>
  );
}

const GanttRow = memo(function GanttRow({
  activity,
  index,
  spanStart,
  spanDays,
  focused,
  selected,
  interactive,
  fitted,
  pxPerDay,
  headerHeight,
  hideRowDelete,
  dropPlacement,
  dragging,
  onRowClick,
  onRename,
  onMove,
  onResize,
  onDelete,
  onAddActivity,
  onToggleLink,
  onReorder,
}: {
  activity: ProgrammeActivity;
  index: number;
  spanStart: string;
  spanDays: number;
  focused: boolean;
  selected: boolean;
  interactive: boolean;
  fitted: boolean;
  pxPerDay: number;
  headerHeight: number;
  hideRowDelete: boolean;
  dropPlacement: "before" | "after" | null;
  dragging: boolean;
  onRowClick: (event: ReactMouseEvent) => void;
  onRename: (name: string) => void;
  onMove: (start: string) => void;
  onResize: (days: number) => void;
  onDelete: () => void;
  onAddActivity: () => void;
  onToggleLink: () => void;
  onReorder: (event: ReactPointerEvent) => void;
}) {
  const [drag, setDrag] = useState<{ kind: "move" | "resize"; delta: number } | null>(
    null,
  );
  const offset = daysBetween(spanStart, activity.start_date) + (drag?.kind === "move" ? drag.delta : 0);
  const duration = Math.max(
    activity.duration_days + (drag?.kind === "resize" ? drag.delta : 0),
    activity.kind === "milestone" ? 0 : 1,
  );
  const top = headerHeight + index * ROW_HEIGHT;
  const leftPct = (offset / spanDays) * 100;
  const widthPct = (duration / spanDays) * 100;
  const chartLeft = interactive
    ? NAME_WIDTH + DATE_WIDTH + DURATION_WIDTH + LINK_WIDTH + PLUS_WIDTH + TRASH_WIDTH
    : NAME_WIDTH;

  function beginDrag(event: ReactPointerEvent, kind: "move" | "resize") {
    if (!interactive) return;
    event.preventDefault();
    event.stopPropagation();
    const originX = event.clientX;
    event.currentTarget.setPointerCapture(event.pointerId);
    const onMovePointer = (moveEvent: PointerEvent) => {
      setDrag({
        kind,
        delta: Math.round((moveEvent.clientX - originX) / Math.max(pxPerDay, 0.25)),
      });
    };
    const onUp = (upEvent: PointerEvent) => {
      window.removeEventListener("pointermove", onMovePointer);
      window.removeEventListener("pointerup", onUp);
      const delta = Math.round((upEvent.clientX - originX) / Math.max(pxPerDay, 0.25));
      setDrag(null);
      if (delta === 0) return;
      if (kind === "move") onMove(addDays(activity.start_date, delta));
      else onResize(Math.max(activity.kind === "milestone" ? 0 : 1, activity.duration_days + delta));
    };
    window.addEventListener("pointermove", onMovePointer);
    window.addEventListener("pointerup", onUp);
  }

  return (
    <div
      className={cn(
        "group/row absolute inset-x-0 select-none",
        (selected || focused) && "bg-[color-mix(in_oklch,var(--sw-beam)_8%,transparent)]",
        selected && "bg-[color-mix(in_oklch,var(--sw-beam)_14%,transparent)]",
        dragging && "opacity-60",
      )}
      style={{ top, height: ROW_HEIGHT }}
      data-activity-key={activity.activity_key}
      role="row"
      aria-selected={selected}
      onClick={onRowClick}
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
          onAddActivity={onAddActivity}
          onToggleLink={onToggleLink}
          onReorder={onReorder}
          hideDelete={hideRowDelete}
        />
      ) : (
        <span
          className={cn(
            "absolute left-0 truncate px-2 text-left text-xs",
            activity.kind === "stage" ? "font-semibold" : "pl-5 text-[var(--sw-text-secondary)]",
          )}
          style={{ width: NAME_WIDTH, top: 8 }}
        >
          {activity.name}
        </span>
      )}
      <div
        className="absolute"
        style={{
          left: fitted
            ? `calc(${chartLeft}px + ${leftPct}%)`
            : chartLeft + offset * pxPerDay,
          width: fitted
            ? `calc(${Math.max(widthPct, 0.8)}% - 8px)`
            : Math.max(duration * pxPerDay, 8),
          top: 10,
          height: 12,
        }}
      >
        {activity.kind === "milestone" ? (
          <button
            type="button"
            aria-label={`Move ${activity.name}`}
            className="size-3 rotate-45 bg-[var(--sw-beam)]"
            onPointerDown={(event) => beginDrag(event, "move")}
            data-interactive={interactive ? "true" : undefined}
          />
        ) : (
          <button
            type="button"
            aria-label={`Move ${activity.name}`}
            className={cn(
              "h-3 w-full rounded-sm",
              activity.kind === "stage" ? "bg-[var(--sw-beam)]/70" : "bg-[var(--sw-beam)]/45",
            )}
            onPointerDown={(event) => beginDrag(event, "move")}
            data-interactive={interactive ? "true" : undefined}
          />
        )}
        {interactive && activity.kind !== "milestone" ? (
          <span
            role="separator"
            aria-label={`Resize ${activity.name}`}
            data-interactive="true"
            className="absolute inset-y-0 right-0 w-2 cursor-ew-resize"
            onPointerDown={(event) => beginDrag(event, "resize")}
          />
        ) : null}
      </div>
    </div>
  );
});

function GanttLinks({
  activities,
  spanStart,
  spanDays,
  fitted,
  pxPerDay,
  leftPane,
  headerHeight,
}: {
  activities: ProgrammeActivity[];
  spanStart: string;
  spanDays: number;
  fitted: boolean;
  pxPerDay: number;
  leftPane: number;
  headerHeight: number;
}) {
  const height = ROW_HEIGHT * Math.max(activities.length, 1);
  const width = fitted ? undefined : Math.max(spanDays * pxPerDay, 8);
  const links = activities.flatMap((activity, index) => {
    if (!activity.predecessor_key) return [];
    const predecessorIndex = activities.findIndex(
      (item) => item.activity_key === activity.predecessor_key,
    );
    const predecessor = activities[predecessorIndex];
    if (!predecessor) return [];
    const fromOffset =
      daysBetween(spanStart, predecessor.start_date) +
      Math.max(predecessor.duration_days, predecessor.kind === "milestone" ? 0 : 1);
    const toOffset = daysBetween(spanStart, activity.start_date);
    return [
      {
        key: `${predecessor.activity_key}->${activity.activity_key}`,
        fromIndex: predecessorIndex,
        toIndex: index,
        fromOffset,
        toOffset,
      },
    ];
  });
  if (!links.length) return null;
  return (
    <svg
      className="pointer-events-none absolute"
      style={{
        left: leftPane,
        top: headerHeight,
        width: fitted ? `calc(100% - ${leftPane}px)` : width,
        height,
      }}
      viewBox={fitted ? `0 0 ${spanDays} ${height}` : undefined}
      preserveAspectRatio={fitted ? "none" : undefined}
    >
      {links.map((link) => {
        const x1 = fitted ? link.fromOffset : link.fromOffset * pxPerDay;
        const x2 = fitted ? link.toOffset : link.toOffset * pxPerDay;
        const y1 = link.fromIndex * ROW_HEIGHT + 16;
        const y2 = link.toIndex * ROW_HEIGHT + 16;
        const mid = x1 + (fitted ? 4 : 8);
        return (
          <path
            key={link.key}
            d={`M ${x1} ${y1} H ${mid} V ${y2} H ${x2}`}
            fill="none"
            stroke="var(--sw-beam)"
            strokeOpacity="0.45"
            strokeWidth={fitted ? Math.max(spanDays / 240, 0.8) : 1.25}
          />
        );
      })}
    </svg>
  );
}

function RowFields({
  activity,
  onRename,
  onMove,
  onResize,
  onDelete,
  onAddActivity,
  onToggleLink,
  onReorder,
  hideDelete,
}: {
  activity: ProgrammeActivity;
  onRename: (name: string) => void;
  onMove: (start: string) => void;
  onResize: (days: number) => void;
  onDelete: () => void;
  onAddActivity: () => void;
  onToggleLink: () => void;
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

  const nameLeft = GRIP_WIDTH + (activity.kind === "stage" ? 2 : 12);
  const actionsLeft = NAME_WIDTH + DATE_WIDTH + DURATION_WIDTH;
  const linked = Boolean(activity.predecessor_key);

  return (
    <>
      <button
        type="button"
        aria-label={`Reorder ${activity.name}`}
        className="absolute top-1 flex h-6 w-4 cursor-grab items-center justify-center text-[var(--sw-text-tertiary)] opacity-0 hover:text-[var(--sw-text-primary)] active:cursor-grabbing group-hover/row:opacity-100 group-focus-within/row:opacity-100"
        style={{ left: 2 }}
        onPointerDown={onReorder}
      >
        <GripVertical className="size-3.5" aria-hidden />
      </button>
      {editingName ? (
        <Input
          autoFocus
          value={draftName}
          aria-label={`${activity.kind} name`}
          className="program-gantt-field absolute top-1 h-6 px-1.5 text-xs"
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
            "absolute top-1 truncate px-1.5 text-left text-xs leading-6",
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
      <div className="absolute top-1" style={{ left: NAME_WIDTH, width: DATE_WIDTH - 6 }}>
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
        className="program-gantt-field absolute top-1 h-6 px-1 text-center text-[11px]"
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
          linked
            ? `Unlink ${activity.name}`
            : `Link ${activity.name} to the previous row`
        }
        aria-pressed={linked}
        title={linked ? "Linked — click to float" : "Floating — click to link to the row above"}
        className={cn(
          "absolute top-1 inline-flex size-5 items-center justify-center rounded-sm text-muted-foreground/70 hover:text-[var(--sw-text-primary)]",
          linked
            ? "text-[var(--sw-beam)] opacity-100"
            : "opacity-0 group-hover/row:opacity-100 group-focus-within/row:opacity-100",
        )}
        style={{ left: actionsLeft }}
        onClick={(event) => {
          event.stopPropagation();
          onToggleLink();
        }}
      >
        {linked ? <Link2 className="size-3.5" aria-hidden /> : <Unlink className="size-3.5" aria-hidden />}
      </button>
      <button
        type="button"
        aria-label={`Add activity below ${activity.name}`}
        className="absolute top-1 inline-flex size-5 items-center justify-center rounded-sm text-muted-foreground/70 opacity-0 hover:text-[var(--sw-text-primary)] group-hover/row:opacity-100 group-focus-within/row:opacity-100"
        style={{ left: actionsLeft + LINK_WIDTH }}
        onClick={(event) => {
          event.stopPropagation();
          onAddActivity();
        }}
      >
        <Plus className="size-3.5" aria-hidden />
      </button>
      {hideDelete ? null : (
        <button
          type="button"
          aria-label={`Delete ${activity.name}`}
          title="Delete"
          className="absolute top-1 inline-flex size-5 items-center justify-center rounded-sm text-muted-foreground/70 opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover/row:opacity-100 group-focus-within/row:opacity-100"
          style={{ left: actionsLeft + LINK_WIDTH + PLUS_WIDTH }}
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
