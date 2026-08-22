import type { Components } from "react-markdown";
import {
  Children,
  cloneElement,
  createContext,
  isValidElement,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  BetweenVerticalEnd,
  BetweenVerticalStart,
  ChevronRight,
  Copy,
  LoaderCircle,
  MoreHorizontal,
  Shield,
  ShieldOff,
  Trash,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  DecisionControl,
  DecisionSchedule,
  groupConsecutiveDecisionFences,
  parseEmbeddedDecision,
  type EmbeddedDecision,
} from "@/components/project/DecisionControl";
import { InlineListItemEditor } from "@/components/project/InlineListItemEditor";
import { InlineMarkdownEditor } from "@/components/project/InlineMarkdownEditor";
import { InlineTableRowEditor } from "@/components/project/InlineTableRowEditor";
import { SitewiseMark } from "@/components/SitewiseMark";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  dropdownMenuItemClassName,
} from "@/components/ui/dropdown-menu";
import {
  maskArtifactBlockMarkers,
  splitTraceQa,
} from "@/lib/artifact-markdown";
import {
  ffeTableLayoutFromHeaders,
  foldFfeScheduleDecisions,
  isFfeDecisionDuplicateRow,
  presentFfeComment,
  presentFfeFinish,
  projectFfeScheduleRow,
  type FfeTableLayout,
} from "@/lib/ffe-schedule-display";
import {
  briefTableLayoutFromHeaders,
  extractCitationTokens,
  isCitationCellValue,
  pmpRegisterTableLayoutFromHeaders,
  stripCitationTokens,
  type RegisterCitationLayout,
} from "@/lib/pmp-register-tables";
import { sourceRangeForRenderedBlock } from "@/lib/inline-markdown";
import type { ArtifactBlockTarget } from "@/lib/artifact-blocks";
import {
  displayTransmittalHeading,
  isTransmittalHeading,
} from "@/lib/transmittal-register";
import {
  splitMarkdownSections,
  type MarkdownSectionSlice,
} from "@/lib/markdown-sections";
import type { MarkdownRange } from "@/lib/markdown-selection";
import {
  editableTableCells,
  expandRangeWithTrailingMarker,
  formatTableRow,
} from "@/lib/table-row-edit";
import type {
  DraftArtifact,
  ProjectDecision,
} from "@/lib/types/project";
import { cn } from "@/lib/utils";

const BLOCK_ID_RE = /<!--\s*clerk:block\s+id=(blk_[a-f0-9]{32})\s*-->/i;

/** Stable plugin identity so react-markdown does not re-parse on every parent render. */
const REMARK_PLUGINS = [remarkGfm];

function blockIdNearRange(
  source: string,
  range: MarkdownRange,
): string | undefined {
  const embedded = source.slice(range.start, range.end).match(BLOCK_ID_RE);
  if (embedded) return embedded[1];
  const preceding = source
    .slice(Math.max(0, range.start - 80), range.start)
    .match(/<!--\s*clerk:block\s+id=(blk_[a-f0-9]{32})\s*-->\s*$/i);
  return preceding?.[1];
}

const EVIDENCE_STATUSES = [
  "Grounded",
  "Partial",
  "Not evidenced",
  "Assumption",
  "Gap",
  "Conflict",
  "Profile",
  "Confirm",
] as const;

/** Column layout hints for markdown tables rendered in the draft sheet. */
type PmpTableLayout = {
  blankFeeNotEvidenced: boolean;
  dropColumnIndexes: readonly number[];
  feeColumnIndex: number | null;
  renameHeaders: Record<string, string>;
  isFfe: boolean;
  finishColumnIndex: number | null;
  commentColumnIndex: number | null;
  citationColumnIndex: number | null;
  appendCitation: boolean;
  blankCitationHeader: boolean;
  ffeLayout: FfeTableLayout | null;
};

const PmpTableLayoutContext = createContext<PmpTableLayout>({
  blankFeeNotEvidenced: false,
  dropColumnIndexes: [],
  feeColumnIndex: null,
  renameHeaders: {},
  isFfe: false,
  finishColumnIndex: null,
  commentColumnIndex: null,
  citationColumnIndex: null,
  appendCitation: false,
  blankCitationHeader: false,
  ffeLayout: null,
});

type FfeDecisionRenderContextValue = {
  projectId?: string;
  decisionsById?: ReadonlyMap<string, ProjectDecision>;
  foldedDecisionsById?: ReadonlyMap<string, EmbeddedDecision>;
  readOnly?: boolean;
  onDraftUpdated?: (draft: DraftArtifact) => void;
};

const FfeDecisionRenderContext = createContext<FfeDecisionRenderContextValue>(
  {},
);

/**
 * Offsets into the source markdown for one block element.
 *
 * `react-markdown` hard-enables `passNode`, and `mdast-util-to-hast` copies the
 * mdast `position` onto every hast node, so every custom component already
 * receives these for free — no rehype plugin and no extra dependency.
 *
 * Block actions slice quoted text out of the *source* using these offsets
 * and never read rendered text back (design decision D1): evidence-cell and
 * decision-fence renderers replace source text with synthesized elements, so
 * rendered text does not map back to markdown.
 */
type MdPositionAttributes = {
  "data-md-start": number;
  "data-md-end": number;
  "data-md-changed"?: string;
};

export type ArtifactBlockComposerState = {
  operation: "ADD" | "UPDATE";
  target: ArtifactBlockTarget;
  placement?: "before" | "after";
  initialContent: string;
};

type InlineEditOptions = {
  sourceMarkdown: string;
  renderedMarkdown: string;
  sourceSections: MarkdownSectionSlice[];
  editingRange?: MarkdownRange | null;
  editingFocusCellIndex?: number;
  isSavingEdit?: boolean;
  editError?: string | null;
  blockComposer?: ArtifactBlockComposerState | null;
  isSavingBlockComposer?: boolean;
  editingCaretPoint?: { x: number; y: number } | null;
  onEditSelection?: (
    range: MarkdownRange,
    options?: {
      focusCellIndex?: number;
      caretPoint?: { x: number; y: number };
    },
  ) => void;
  onEditWithAi?: (range: MarkdownRange, rect: DOMRect) => void;
  onCancelSelectionEdit?: () => void;
  onSaveSelectionEdit?: (range: MarkdownRange, markdown: string) => Promise<void>;
  onCancelBlockComposer?: () => void;
  onSaveBlockComposer?: (content: string) => void;
  onMutateBlock?: (
    operation:
      | "ADD"
      | "DELETE"
      | "DUPLICATE"
      | "PROTECT"
      | "UNPROTECT"
      | "KEEP"
      | "CONFIRM_DELETE",
    target: ArtifactBlockTarget,
    placement?: "before" | "after",
  ) => void;
  protectedBlockIds?: Set<string>;
  reviewBlockStatuses?: Map<string, "conflict" | "propose_delete">;
  informationRegisterOpen?: boolean;
  onToggleInformationRegister?: () => void;
  onLoadTransmittal?: () => void;
  canLoadTransmittal?: boolean;
  onSaveTransmittal?: () => void;
  canSaveTransmittal?: boolean;
  isSavingTransmittal?: boolean;
  transmittalSaveError?: string | null;
};

/**
 * Live render options for the stable react-markdown component map.
 *
 * Recreating `p` / `tr` / `table` function identities remounts inline editors
 * and wipes in-progress typing (a parent poll used to do this every few
 * seconds). The map is created once; renderers read this context each time.
 */
type MarkdownRenderState = {
  version?: number;
  hideLeadingHeading?: boolean;
  changedRanges: readonly MarkdownRange[];
  projectTitle?: string;
  projectId?: string;
  decisionsById?: ReadonlyMap<string, ProjectDecision>;
  foldedDecisionsById?: ReadonlyMap<string, EmbeddedDecision>;
  readOnly?: boolean;
  onDraftUpdated?: (draft: DraftArtifact) => void;
} & InlineEditOptions;

const EMPTY_RENDER_STATE: MarkdownRenderState = {
  changedRanges: [],
  sourceMarkdown: "",
  renderedMarkdown: "",
  sourceSections: [],
};

const MarkdownRenderContext =
  createContext<MarkdownRenderState>(EMPTY_RENDER_STATE);

function useMarkdownRender(): MarkdownRenderState {
  return useContext(MarkdownRenderContext);
}

function markdownBlockTarget(
  state: MarkdownRenderState,
  node: unknown,
  type: ArtifactBlockTarget["type"],
): ArtifactBlockTarget | null {
  const attributes = mdPosition(node, state.changedRanges);
  if (!attributes || !state.sourceMarkdown) return null;
  const renderedRange = {
    start: attributes["data-md-start"],
    end: attributes["data-md-end"],
  };
  const mapped = sourceRangeForRenderedBlock(
    state.sourceMarkdown,
    state.renderedMarkdown,
    renderedRange,
  );
  if (!mapped) return null;
  const range = expandRangeWithTrailingMarker(state.sourceMarkdown, mapped);
  const section = state.sourceSections.find(
    (item) => item.start <= range.start && range.start < item.end,
  );
  if (!section) return null;
  const blockId = blockIdNearRange(state.sourceMarkdown, range);
  return {
    ...(blockId ? { id: blockId } : {}),
    type,
    range,
    sectionStart: section.start,
  };
}

function isLeadingH1(source: string, start: number | undefined): boolean {
  if (start == null) return true;
  return !/(^|\n)# /.test(source.slice(0, start));
}

function blockActionsKey(target: ArtifactBlockTarget): string {
  return `${target.type}:${target.range.start}:${target.range.end}`;
}

/** Chrome-free insert: looks like a normal block, Escape/empty blur discards. */
function ArtifactBlockComposer({
  blockType,
  initialContent,
  isSaving,
  onCancel,
  onSave,
}: {
  blockType: ArtifactBlockTarget["type"];
  initialContent: string;
  isSaving: boolean;
  onCancel: () => void;
  onSave: (content: string) => void;
}) {
  if (blockType === "table_row") {
    return (
      <InlineTableRowEditor
        sourceRow={initialContent}
        sourceStart={0}
        sourceEnd={0}
        isSaving={isSaving}
        onCancel={onCancel}
        onSave={async (markdown) => {
          if (!markdown.replace(/\|/g, "").trim()) {
            onCancel();
            return;
          }
          onSave(markdown);
        }}
      />
    );
  }

  if (blockType === "list_item") {
    return (
      <PendingListItemInsert
        initialContent={initialContent}
        isSaving={isSaving}
        onCancel={onCancel}
        onSave={onSave}
      />
    );
  }

  return (
    <PendingParagraphInsert
      isSaving={isSaving}
      onCancel={onCancel}
      onSave={onSave}
    />
  );
}

function PendingParagraphInsert({
  isSaving,
  onCancel,
  onSave,
}: {
  isSaving: boolean;
  onCancel: () => void;
  onSave: (content: string) => void;
}) {
  const editorRef = useRef<HTMLParagraphElement>(null);
  const dirtyRef = useRef(false);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    editor.focus();
    editor.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, []);

  function commitOrDiscard() {
    const text = (editorRef.current?.innerText ?? "").replace(/\u00a0/g, " ").trim();
    if (!text) {
      onCancel();
      return;
    }
    onSave(text);
  }

  return (
    <p
      ref={editorRef}
      role="textbox"
      aria-label="Add paragraph"
      aria-multiline="true"
      aria-busy={isSaving}
      contentEditable={!isSaving}
      suppressContentEditableWarning
      spellCheck
      data-block-composer
      data-instruction-ui
      className="my-3 min-h-5 whitespace-pre-wrap leading-relaxed caret-[var(--sw-beam-hex)] outline-none"
      onInput={() => {
        dirtyRef.current = true;
      }}
      onKeyDown={(event) => {
        if (event.nativeEvent.isComposing) return;
        if (event.key === "Escape") {
          event.preventDefault();
          onCancel();
          return;
        }
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          commitOrDiscard();
        }
      }}
      onBlur={(event) => {
        const next = event.relatedTarget;
        if (next instanceof Node && editorRef.current?.contains(next)) return;
        if (!dirtyRef.current) {
          onCancel();
          return;
        }
        commitOrDiscard();
      }}
    />
  );
}

function PendingListItemInsert({
  initialContent,
  isSaving,
  onCancel,
  onSave,
}: {
  initialContent: string;
  isSaving: boolean;
  onCancel: () => void;
  onSave: (content: string) => void;
}) {
  const marker =
    initialContent.match(/^\s*(?:[-*+] |\d+[.)] )/)?.[0]?.trimStart() ?? "- ";
  return (
    <InlineListItemEditor
      sourceItem={initialContent || marker}
      sourceStart={0}
      sourceEnd={0}
      isSaving={isSaving}
      onCancel={onCancel}
      onSave={async (markdown) => {
        const body = markdown.replace(/^\s*(?:[-*+] |\d+[.)] )/, "").trim();
        if (!body) {
          onCancel();
          return;
        }
        onSave(markdown);
      }}
    >
      {null}
    </InlineListItemEditor>
  );
}

function composerForTarget(
  target: ArtifactBlockTarget | null | undefined,
  options?: InlineEditOptions,
): ReactNode {
  const composer = options?.blockComposer;
  if (
    !composer ||
    !target ||
    !rangesEqual(composer.target.range, target.range) ||
    !options.onCancelBlockComposer ||
    !options.onSaveBlockComposer
  ) {
    return null;
  }
  return (
    <ArtifactBlockComposer
      blockType={composer.target.type}
      initialContent={composer.initialContent}
      isSaving={Boolean(options.isSavingBlockComposer)}
      onCancel={options.onCancelBlockComposer}
      onSave={options.onSaveBlockComposer}
    />
  );
}

/** Narrow right slot for the ⋯ menu so citations/content keep max width. */
const BLOCK_ACTIONS_SLOT_CLASS =
  "flex h-6 w-6 shrink-0 items-center justify-end print:hidden";

/**
 * Resting: muted grey icons, no black chip. Hover keeps outline beam treatment.
 * Opacity is instant so the trigger is clickable as soon as the pointer hits the row.
 */
const BLOCK_ACTION_BUTTON_CLASS =
  "border-transparent bg-transparent text-muted-foreground shadow-none opacity-0 group-hover/block:opacity-100 group-focus-within/block:opacity-100 focus-visible:opacity-100 aria-expanded:opacity-100";

type BlockActionsUi = {
  openActionsKey: string | null;
  onOpenActionsKeyChange: (key: string | null) => void;
};

const BlockActionsUiContext = createContext<BlockActionsUi>({
  openActionsKey: null,
  onOpenActionsKeyChange: () => {},
});

function BlockActionsProvider({ children }: { children: ReactNode }) {
  const [openActionsKey, setOpenActionsKey] = useState<string | null>(null);
  const value = useMemo(
    () => ({
      openActionsKey,
      onOpenActionsKeyChange: setOpenActionsKey,
    }),
    [openActionsKey],
  );
  return (
    <BlockActionsUiContext.Provider value={value}>
      {children}
    </BlockActionsUiContext.Provider>
  );
}

const ICON_MENU_ITEM_CLASS = cn(
  dropdownMenuItemClassName,
  "justify-center px-2 py-2",
);
const MENU_ICON_CLASS = "size-3.5 shrink-0";

function IconMenuItem({
  label,
  onSelect,
  variant = "default",
  children,
}: {
  label: string;
  onSelect: () => void;
  variant?: "default" | "destructive";
  children: ReactNode;
}) {
  return (
    <DropdownMenuItem
      aria-label={label}
      title={label}
      variant={variant}
      className={ICON_MENU_ITEM_CLASS}
      onSelect={onSelect}
    >
      {children}
    </DropdownMenuItem>
  );
}

function blockActionsAvailable(
  target: ArtifactBlockTarget | null | undefined,
  options?: InlineEditOptions,
): boolean {
  if (!target || !options) return false;
  return Boolean(options.onEditWithAi || options.onMutateBlock);
}

function BlockHoverActions({
  target,
  options,
}: {
  target: ArtifactBlockTarget;
  options?: InlineEditOptions;
}) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const { openActionsKey, onOpenActionsKeyChange } =
    useContext(BlockActionsUiContext);
  const actionsKey = blockActionsKey(target);
  const menuOpen = openActionsKey === actionsKey;
  const available = blockActionsAvailable(target, options);
  const interactive =
    available && !options?.editingRange && !options?.blockComposer;
  const blockId = target.id;
  const reviewStatus = blockId
    ? options?.reviewBlockStatuses?.get(blockId)
    : undefined;
  const isProtected = Boolean(
    blockId && options?.protectedBlockIds?.has(blockId),
  );
  const label = blockLabel(target.type);

  // Keep the trigger mounted. CSS hides it until row hover so the first
  // click does not wait for a markdown remount.
  if (!available) return null;

  return (
    <div
      className={BLOCK_ACTIONS_SLOT_CLASS}
      data-instruction-ui={interactive ? "" : undefined}
      data-block-actions
    >
      {interactive ? (
        <DropdownMenu
          open={menuOpen}
          onOpenChange={(open) =>
            onOpenActionsKeyChange(open ? actionsKey : null)
          }
        >
          <DropdownMenuTrigger asChild>
            <Button
              ref={triggerRef}
              type="button"
              size="icon-xs"
              variant="outline"
              className={BLOCK_ACTION_BUTTON_CLASS}
              aria-label={`${label} actions`}
              title="Actions"
            >
              <MoreHorizontal aria-hidden className="size-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            sideOffset={4}
            className="min-w-0 w-auto"
            data-instruction-ui=""
          >
              {options?.onEditWithAi ? (
                <IconMenuItem
                  label={`Edit ${label} with AI`}
                  onSelect={() => {
                    const rect =
                      triggerRef.current?.getBoundingClientRect() ??
                      new DOMRect();
                    options.onEditWithAi?.(target.range, rect);
                  }}
                >
                  <SitewiseMark
                    size={14}
                    variant="solid"
                    className="p-0"
                    title=""
                  />
                </IconMenuItem>
              ) : null}
              {options?.onMutateBlock ? (
                <>
                  <IconMenuItem
                    label={`Add ${label} above`}
                    onSelect={() =>
                      options.onMutateBlock?.("ADD", target, "before")
                    }
                  >
                    <BetweenVerticalStart
                      className={MENU_ICON_CLASS}
                      aria-hidden
                    />
                  </IconMenuItem>
                  <IconMenuItem
                    label={`Add ${label} below`}
                    onSelect={() =>
                      options.onMutateBlock?.("ADD", target, "after")
                    }
                  >
                    <BetweenVerticalEnd
                      className={MENU_ICON_CLASS}
                      aria-hidden
                    />
                  </IconMenuItem>
                </>
              ) : null}
              {options?.onMutateBlock && blockId ? (
                <IconMenuItem
                  label={
                    isProtected ? `Unprotect ${label}` : `Protect ${label}`
                  }
                  onSelect={() =>
                    options.onMutateBlock?.(
                      isProtected ? "UNPROTECT" : "PROTECT",
                      target,
                    )
                  }
                >
                  {isProtected ? (
                    <ShieldOff className={MENU_ICON_CLASS} aria-hidden />
                  ) : (
                    <Shield className={MENU_ICON_CLASS} aria-hidden />
                  )}
                </IconMenuItem>
              ) : null}
              {options?.onMutateBlock ? (
                <>
                  <IconMenuItem
                    label={`Duplicate ${label}`}
                    onSelect={() =>
                      options.onMutateBlock?.("DUPLICATE", target)
                    }
                  >
                    <Copy className={MENU_ICON_CLASS} aria-hidden />
                  </IconMenuItem>
                  <IconMenuItem
                    label={`Delete ${label}`}
                    variant="destructive"
                    onSelect={() => options.onMutateBlock?.("DELETE", target)}
                  >
                    <Trash className={MENU_ICON_CLASS} aria-hidden />
                  </IconMenuItem>
                </>
              ) : null}
              {options?.onMutateBlock && reviewStatus === "conflict" ? (
                <IconMenuItem
                  label={`Keep ${label} after refresh conflict`}
                  onSelect={() => options.onMutateBlock?.("KEEP", target)}
                >
                  <Shield className={MENU_ICON_CLASS} aria-hidden />
                </IconMenuItem>
              ) : null}
              {options?.onMutateBlock && reviewStatus === "propose_delete" ? (
                <>
                  <IconMenuItem
                    label={`Keep ${label} proposed for deletion`}
                    onSelect={() => options.onMutateBlock?.("KEEP", target)}
                  >
                    <Shield className={MENU_ICON_CLASS} aria-hidden />
                  </IconMenuItem>
                  <IconMenuItem
                    label={`Confirm delete ${label}`}
                    variant="destructive"
                    onSelect={() =>
                      options.onMutateBlock?.("CONFIRM_DELETE", target)
                    }
                  >
                    <Trash className={MENU_ICON_CLASS} aria-hidden />
                  </IconMenuItem>
                </>
              ) : null}
          </DropdownMenuContent>
        </DropdownMenu>
      ) : null}
    </div>
  );
}

function composerPlacement(
  options?: InlineEditOptions,
): "before" | "after" | null {
  const composer = options?.blockComposer;
  if (!composer) return null;
  if (composer.operation === "ADD") return composer.placement ?? "after";
  return "before";
}

function withAdjacentComposer(
  target: ArtifactBlockTarget | null | undefined,
  block: ReactNode,
  options?: InlineEditOptions,
): ReactNode {
  const form = composerForTarget(target, options);
  const placement = composerPlacement(options);
  if (!form || !placement) return block;
  return (
    <>
      {placement === "before" ? form : null}
      {block}
      {placement === "after" ? form : null}
    </>
  );
}

function mdPosition(
  node: unknown,
  changedRanges: readonly MarkdownRange[],
): MdPositionAttributes | undefined {
  const position = (
    node as {
      position?: { start?: { offset?: number }; end?: { offset?: number } };
    } | null
  )?.position;
  const start = position?.start?.offset;
  const end = position?.end?.offset;
  if (typeof start !== "number" || typeof end !== "number") return undefined;
  const changed = changedRanges.some(
    (range) => range.start < end && range.end > start,
  );
  return changed
    ? { "data-md-start": start, "data-md-end": end, "data-md-changed": "" }
    : { "data-md-start": start, "data-md-end": end };
}

function baseComponents(): Components {
  return {
    h1: ({ children }) => (
      <h1 className="mb-4 text-2xl font-semibold leading-tight">{children}</h1>
    ),
    h2: function MarkdownH2Base({ children, node }) {
      const { changedRanges } = useMarkdownRender();
      return (
        <h2
          className="pmp-section-heading mt-8 border-b pb-2 text-lg font-semibold first:mt-0"
          {...mdPosition(node, changedRanges)}
        >
          {children}
        </h2>
      );
    },
    h3: function MarkdownH3({ children, node }) {
      const { changedRanges } = useMarkdownRender();
      return flattenText(children).trim().toLowerCase() === "critical current position" ? null : (
        <h3 className="mt-5 text-base font-semibold" {...mdPosition(node, changedRanges)}>
          {children}
        </h3>
      );
    },
    h4: function MarkdownH4({ children, node }) {
      const { changedRanges } = useMarkdownRender();
      return (
        <h4 className="mt-4 text-sm font-semibold" {...mdPosition(node, changedRanges)}>
          {children}
        </h4>
      );
    },
    p: function MarkdownParagraph({ children, node }) {
      const editOptions = useMarkdownRender();
      const position = (item: unknown) => mdPosition(item, editOptions.changedRanges);
      const text = flattenText(children);
      if (isPmpGovernanceDisclaimer(text)) return null;
      const ownerBrief = stripOwnerBriefLeadIn(text);
      const visibleText = stripEvidenceOnFileLabel(stripUserProvidedLabel(ownerBrief));
      if (visibleText !== text && !visibleText) return null;

      const attributes = position(node);
      const renderedRange = attributes
        ? {
            start: attributes["data-md-start"],
            end: attributes["data-md-end"],
          }
        : null;
      const sourceRange =
        renderedRange && editOptions
          ? sourceRangeForRenderedBlock(
              editOptions.sourceMarkdown,
              editOptions.renderedMarkdown,
              renderedRange,
            )
          : null;
      const isEditing = rangesEqual(editOptions?.editingRange, sourceRange);
      const section = sourceRange
        ? editOptions?.sourceSections.find(
            (item) => item.start <= sourceRange.start && sourceRange.start < item.end,
          )
        : null;
      const paragraphBlockId =
        sourceRange && editOptions
          ? blockIdNearRange(editOptions.sourceMarkdown, sourceRange)
          : undefined;
      const paragraphTarget =
        sourceRange && section
          ? {
              ...(paragraphBlockId ? { id: paragraphBlockId } : {}),
              range: sourceRange,
              sectionStart: section.start,
              type: "paragraph" as const,
            }
          : null;
      const canTargetParagraph =
        visibleText === text &&
        paragraphTarget !== null &&
        Boolean(
          editOptions?.onEditSelection ||
            editOptions?.onEditWithAi ||
            editOptions?.onMutateBlock,
        ) &&
        !editOptions?.blockComposer &&
        (!editOptions?.editingRange || isEditing);

      if (
        isEditing &&
        sourceRange &&
        paragraphTarget &&
        editOptions?.onCancelSelectionEdit &&
        editOptions.onSaveSelectionEdit
      ) {
        const reserveActions = blockActionsAvailable(
          paragraphTarget,
          editOptions,
        );
        return withAdjacentComposer(
          paragraphTarget,
          <div className="group/block relative my-3 flex items-start gap-2">
            <InlineMarkdownEditor
              sectionStart={section?.start ?? sourceRange.start}
              sourceStart={sourceRange.start}
              sourceEnd={sourceRange.end}
              isChanged={attributes?.["data-md-changed"] !== undefined}
              isSaving={Boolean(editOptions.isSavingEdit)}
              error={editOptions.editError}
              caretPoint={editOptions.editingCaretPoint}
              className="min-w-0 flex-1"
              onCancel={editOptions.onCancelSelectionEdit}
              onSave={(markdown) =>
                editOptions.onSaveSelectionEdit?.(sourceRange, markdown) ??
                Promise.resolve()
              }
            >
              {children}
            </InlineMarkdownEditor>
            {/* Keep the actions slot reserved so edit mode does not widen text. */}
            {reserveActions ? (
              <div className={BLOCK_ACTIONS_SLOT_CLASS} aria-hidden />
            ) : null}
          </div>,
          editOptions,
        );
      }

      if (canTargetParagraph && paragraphTarget && sourceRange) {
        return withAdjacentComposer(
          paragraphTarget,
          <div className="group/block relative my-3 flex items-start gap-2">
            <p
              className="min-w-0 flex-1 leading-relaxed"
              {...attributes}
              onDoubleClick={(event) => {
                if (!editOptions?.onEditSelection) return;
                event.preventDefault();
                editOptions.onEditSelection(sourceRange, {
                  caretPoint: { x: event.clientX, y: event.clientY },
                });
              }}
            >
              {children}
            </p>
            <BlockHoverActions target={paragraphTarget} options={editOptions} />
          </div>,
          editOptions,
        );
      }

      const staticParagraph = (
        <p className="my-3 leading-relaxed" {...attributes}>
          {visibleText === text ? children : visibleText}
        </p>
      );
      return paragraphTarget
        ? withAdjacentComposer(paragraphTarget, staticParagraph, editOptions)
        : staticParagraph;
    },
    a: ({ children, href }) => (
      <a className="font-medium text-primary underline underline-offset-2" href={href}>
        {children}
      </a>
    ),
    blockquote: function MarkdownBlockquote({ children, node }) {
      const { changedRanges } = useMarkdownRender();
      return (
        <blockquote
          className="my-4 border-l-2 pl-4 text-muted-foreground"
          {...mdPosition(node, changedRanges)}
        >
          {children}
        </blockquote>
      );
    },
    hr: () => <hr className="my-6 border-border" />,
    ul: ({ children }) => (
      <ul className="my-3 list-disc space-y-1.5 pl-5 leading-relaxed">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="my-3 list-decimal space-y-1.5 pl-5 leading-relaxed">{children}</ol>
    ),
    li: function MarkdownListItem({ children, node }) {
      const editOptions = useMarkdownRender();
      const position = (item: unknown) => mdPosition(item, editOptions.changedRanges);
      const text = flattenText(children);
      const visibleText = stripEvidenceOnFileLabel(stripUserProvidedLabel(text));
      if (visibleText !== text && !visibleText) return null;
      const target = markdownBlockTarget(editOptions, node, "list_item");
      const isEditing = rangesEqual(editOptions?.editingRange, target?.range);
      if (
        isEditing &&
        target &&
        editOptions?.onCancelSelectionEdit &&
        editOptions.onSaveSelectionEdit
      ) {
        const sourceItem = editOptions.sourceMarkdown.slice(
          target.range.start,
          target.range.end,
        );
        return (
          <InlineListItemEditor
            sourceItem={sourceItem}
            sourceStart={target.range.start}
            sourceEnd={target.range.end}
            isSaving={Boolean(editOptions.isSavingEdit)}
            error={editOptions.editError}
            onCancel={editOptions.onCancelSelectionEdit}
            onSave={(markdown) =>
              editOptions.onSaveSelectionEdit?.(target.range, markdown) ??
              Promise.resolve()
            }
          >
            {visibleText === text ? children : visibleText}
          </InlineListItemEditor>
        );
      }
      const canEdit =
        target !== null &&
        Boolean(
          editOptions?.onEditSelection ||
            editOptions?.onEditWithAi ||
            editOptions?.onMutateBlock,
        ) &&
        !editOptions?.editingRange &&
        !editOptions?.blockComposer;
      const form = composerForTarget(target, editOptions);
      const placement = composerPlacement(editOptions);
      const item = (
        <li
          className="group/block relative list-item leading-relaxed"
          {...position(node)}
          data-block-type="list_item"
          onDoubleClick={
            canEdit && editOptions?.onEditSelection
              ? (event) => {
                  event.preventDefault();
                  editOptions.onEditSelection?.(target.range, {
                    caretPoint: { x: event.clientX, y: event.clientY },
                  });
                }
              : undefined
          }
        >
          <span className="flex items-start gap-2">
            <span className="min-w-0 flex-1">
              {visibleText === text ? children : visibleText}
            </span>
            {target ? (
              <BlockHoverActions target={target} options={editOptions} />
            ) : null}
          </span>
        </li>
      );
      if (!form || !placement) return item;
      return (
        <>
          {placement === "before" ? form : null}
          {item}
          {placement === "after" ? form : null}
        </>
      );
    },
    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
    code: ({ children, className }) => {
      const language = className?.replace("language-", "") ?? "";
      if (language === "pmp-decision" || language === "pmp-decision-group") {
        return (
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{children}</code>
        );
      }
      return (
        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{children}</code>
      );
    },
    table: function MarkdownTable({ children }) {
      const editOptions = useMarkdownRender();
      const projectTitle = editOptions.projectTitle;
      const isInformationRegister = informationRegisterTable(children);
      const headers = headerLabelsFromTable(children);
      const consultantsLayout = consultantsTableLayout(children);
      const isConsultants = consultantsLayout !== null;
      const ffeLayout = ffeTableLayoutFromHeaders(headers);
      const isFfe = ffeLayout !== null;
      const collapsed =
        isInformationRegister && editOptions?.informationRegisterOpen === false;
      return (
        <PmpTableLayoutContext.Provider
          value={tableLayoutFor(headers, consultantsLayout, ffeLayout)}
        >
          <div
            id={isInformationRegister ? "project-documents-register" : undefined}
            className={[
              "my-4 overflow-x-auto border pmp-table-wrap",
              collapsed ? "hidden print:block" : "",
            ].join(" ")}
          >
            <table
              className={[
                "w-full border-collapse text-left text-sm",
                isConsultants
                  ? "min-w-[52rem] table-fixed pmp-table-consultants"
                  : isFfe
                    ? "min-w-[28rem] pmp-table-ffe"
                    : "min-w-[32rem]",
              ].join(" ")}
            >
              {isConsultants ? (
                <colgroup>
                  <col className="pmp-col-discipline" />
                  <col className="pmp-col-firm" />
                  <col className="pmp-col-fee" />
                  <col className="pmp-col-status" />
                  <col className="pmp-col-citation" />
                </colgroup>
              ) : null}
              {normalizeSummaryTable(children, projectTitle)}
            </table>
          </div>
        </PmpTableLayoutContext.Provider>
      );
    },
    thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
    th: ({ children }) => (
      <th className="border-b px-3 py-2 align-top font-medium text-foreground">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="border-b px-3 py-2 align-middle text-foreground">
        {children}
      </td>
    ),
    // `tr` is the addressable unit for a table, never `td`/`th` — renderEvidenceCell
    // replaces cell content with badges, so a cell's rendered text is not its source.
    tr: function MarkdownTableRowHost({ children, node }) {
      const state = useMarkdownRender();
      return (
      <MarkdownTableRow
        node={node}
        projectTitle={state.projectTitle}
        editOptions={state}
        position={(item) => mdPosition(item, state.changedRanges)}
        blockTarget={(item, type) => markdownBlockTarget(state, item, type)}
      >
        {children}
      </MarkdownTableRow>
      );
    },
  };
}

function MarkdownTableRow({
  children,
  node,
  projectTitle,
  editOptions,
  position,
  blockTarget,
}: {
  children?: ReactNode;
  node?: unknown;
  projectTitle?: string;
  editOptions?: InlineEditOptions;
  position: (node: unknown) => MdPositionAttributes | undefined;
  blockTarget: (
    node: unknown,
    type: ArtifactBlockTarget["type"],
  ) => ArtifactBlockTarget | null;
}) {
  const {
    blankFeeNotEvidenced,
    dropColumnIndexes,
    feeColumnIndex,
    renameHeaders,
    isFfe,
    finishColumnIndex,
    commentColumnIndex,
    citationColumnIndex,
    appendCitation,
    blankCitationHeader,
    ffeLayout,
  } = useContext(PmpTableLayoutContext);
  const { foldedDecisionsById } = useContext(FfeDecisionRenderContext);
  const firstCell = Children.toArray(children)[0];
  const label = summaryLabel(firstCell);
  if (label === "critical current position" || label === "field") return null;
  const isHeader =
    isValidElement(firstCell) && String(firstCell.type).toLowerCase() === "th";
  if (
    isFfe &&
    !isHeader &&
    isFfeDecisionDuplicateRow(flattenText(firstCell), foldedDecisionsById)
  ) {
    return null;
  }
  const target = isHeader ? null : blockTarget(node, "table_row");
  const isEditing = rangesEqual(editOptions?.editingRange, target?.range);
  if (
    isEditing &&
    target &&
    editOptions?.onCancelSelectionEdit &&
    editOptions.onSaveSelectionEdit
  ) {
    const sourceRow = editOptions.sourceMarkdown.slice(
      target.range.start,
      target.range.end,
    );
    const projected = isFfe ? projectFfeScheduleRow(sourceRow, ffeLayout) : null;
    const editorRow = projected
      ? formatTableRow(
          projected.cells.map((cell, index) => {
            if (index === 2) {
              return presentFfeFinish(
                projected.cells[0] ?? "",
                cell,
                foldedDecisionsById,
              );
            }
            if (index === 3) return presentFfeComment(cell);
            return cell;
          }),
        )
      : sourceRow;
    return (
      <InlineTableRowEditor
        sourceRow={editorRow}
        sourceStart={target.range.start}
        sourceEnd={target.range.end}
        isSaving={Boolean(editOptions.isSavingEdit)}
        error={editOptions.editError}
        focusCellIndex={editOptions.editingFocusCellIndex ?? 0}
        onCancel={editOptions.onCancelSelectionEdit}
        onSave={(markdown) =>
          editOptions.onSaveSelectionEdit?.(
            target.range,
            projected
              ? projected.commit(editableTableCells(markdown))
              : markdown,
          ) ?? Promise.resolve()
        }
      />
    );
  }
  const canEdit =
    target !== null &&
    Boolean(
      editOptions?.onEditSelection ||
        editOptions?.onEditWithAi ||
        editOptions?.onMutateBlock,
    ) &&
    !editOptions?.editingRange &&
    !editOptions?.blockComposer;
  const conflicted = rowHasConflict(children);
  const itemName = flattenText(firstCell);
  const prepared = Children.toArray(children).map((cell, sourceIndex) => {
    if (!isValidElement<{ children?: ReactNode }>(cell)) return cell;
    const raw = cell.props.children;
    const renamed = renameHeaders[flattenText(raw).trim().toLowerCase()];
    if (renamed) {
      return cloneElement(cell, { key: `cell-${sourceIndex}` }, renamed);
    }
    if (isFfe && finishColumnIndex === sourceIndex) {
      return cloneElement(
        cell,
        { key: `cell-${sourceIndex}` },
        presentFfeFinish(itemName, flattenText(raw), foldedDecisionsById),
      );
    }
    if (isFfe && commentColumnIndex === sourceIndex) {
      return cloneElement(
        cell,
        { key: `cell-${sourceIndex}` },
        presentFfeComment(flattenText(raw)),
      );
    }
    if (isFfe) {
      const text = flattenText(raw).trim();
      if (/^not evidenced$/i.test(text)) {
        return cloneElement(cell, { key: `cell-${sourceIndex}` }, "");
      }
    }
    return cell;
  });
  const harvested =
    isHeader || !(appendCitation || citationColumnIndex !== null)
      ? ""
      : harvestRowCitations(prepared);
  const sourceCells = prepared.filter((_, index) => {
    return !dropColumnIndexes.includes(index);
  });
  const remainingSourceIndexes = prepared
    .map((_, index) => index)
    .filter((index) => !dropColumnIndexes.includes(index));
  const liftCitations = appendCitation || citationColumnIndex !== null;
  const cells = sourceCells.map((cell, index) => {
    if (!isValidElement<{ children?: ReactNode }>(cell)) return cell;
    const sourceIndex = remainingSourceIndexes[index];
    const isCitationCol = sourceIndex === citationColumnIndex;
    if (isHeader && isCitationCol && blankCitationHeader) {
      return cloneElement(cell, { key: `cell-${index}` }, "");
    }
    const raw = cell.props.children;
    const blankFee =
      blankFeeNotEvidenced &&
      feeColumnIndex !== null &&
      index === feeColumnIndex &&
      /^not evidenced$/i.test(flattenText(raw).trim());
    let content: ReactNode = raw;
    if (blankFee) {
      content = "";
    } else if (isCitationCol) {
      const citation = harvested || citationDisplayValue(flattenText(raw));
      content = renderEvidenceCell(citation, { conflicted });
    } else if (!isHeader && liftCitations) {
      const text = flattenText(raw);
      const stripped = stripCitationTokens(text);
      const next = stripped !== text ? stripped : raw;
      content = isFfe ? next : renderEvidenceCell(next, { conflicted });
    } else if (!isHeader) {
      content = isFfe ? raw : renderEvidenceCell(raw, { conflicted });
    }
    return cloneElement(cell, { key: `cell-${index}` }, content);
  });
  const withCitation =
    appendCitation && cells.length
      ? [
          ...cells,
          appendTrailingCell(
            cells[cells.length - 1],
            isHeader ? "" : renderEvidenceCell(harvested, { conflicted }),
          ),
        ]
      : cells;
  const normalized = Children.toArray(
    normalizeSummaryRow(withCitation, projectTitle),
  );
  const reserveRowActions = Boolean(
    target && blockActionsAvailable(target, editOptions),
  );
  const rowCells =
    reserveRowActions && target
      ? normalized.map((cell, index, all) => {
          if (index !== all.length - 1) return cell;
          if (!isValidElement<{ children?: ReactNode }>(cell)) return cell;
          return cloneElement(cell, {
            key: cell.key ?? `cell-actions-${index}`,
            children: (
              <div className="flex items-start justify-end gap-2">
                <div
                  className={blankFeeNotEvidenced ? "shrink-0" : "min-w-0"}
                >
                  {cell.props.children}
                </div>
                <BlockHoverActions target={target} options={editOptions} />
              </div>
            ),
          });
        })
      : normalized;
  const row = (
    <tr
      className="group/block sw-table-row even:bg-muted/20"
      {...position(node)}
      data-block-type={target ? "table_row" : undefined}
      onDoubleClick={
        canEdit && editOptions?.onEditSelection
          ? (event) => {
              event.preventDefault();
              const cell = (event.target as HTMLElement | null)?.closest(
                "td,th",
              );
              const cellIndex = cell
                ? Array.from(
                    event.currentTarget.querySelectorAll("td,th"),
                  ).indexOf(cell)
                : 0;
              editOptions.onEditSelection?.(target.range, {
                focusCellIndex: Math.max(0, cellIndex),
              });
            }
          : undefined
      }
    >
      {rowCells}
    </tr>
  );
  const form = composerForTarget(target, editOptions);
  const placement = composerPlacement(editOptions);
  if (!form || !placement) return row;
  return (
    <>
      {placement === "before" ? form : null}
      {row}
      {placement === "after" ? form : null}
    </>
  );
}

function markdownComponents(): Components {
  return {
    ...baseComponents(),
    pre: function MarkdownPre({ children }) {
      const options = useMarkdownRender();
      const child = Array.isArray(children) ? children[0] : children;
      if (
        typeof child === "object" &&
        child !== null &&
        "props" in child &&
        typeof child.props === "object" &&
        child.props !== null &&
        "className" in child.props &&
        typeof child.props.className === "string"
      ) {
        const className = child.props.className;
        const raw = String("children" in child.props ? child.props.children : "").trim();

        if (className.includes("language-pmp-decision-group")) {
          if (options.projectId) {
            const decisions = parseDecisionGroup(raw, options.decisionsById);
            if (decisions.length) {
              return (
                <DecisionSchedule
                  projectId={options.projectId}
                  decisions={decisions}
                  readOnly={options.readOnly || !options.decisionsById}
                  onDraftUpdated={options.onDraftUpdated}
                />
              );
            }
          }
          return (
            <pre className="my-4 overflow-x-auto border bg-muted/30 p-3 text-xs">
              {children}
            </pre>
          );
        }

        if (/\blanguage-pmp-decision\b/.test(className)) {
          const embedded = parseEmbeddedDecision(raw);
          const decision = embedded
            ? hydrateEmbeddedDecision(
                embedded,
                options.decisionsById?.get(embedded.id),
              )
            : null;
          if (decision && options.projectId) {
            return (
              <DecisionControl
                key={`${decision.id}:${decision.revision ?? 0}:${decision.set_revision ?? 0}`}
                projectId={options.projectId}
                decision={decision}
                readOnly={options.readOnly || !options.decisionsById}
                onDraftUpdated={options.onDraftUpdated}
              />
            );
          }
          return (
            <pre className="my-4 overflow-x-auto border bg-muted/30 p-3 text-xs">
              {children}
            </pre>
          );
        }
      }
      return (
        <pre className="my-4 overflow-x-auto border bg-muted/30 p-3 text-xs">
          {children}
        </pre>
      );
    },
    h1: function MarkdownH1({ children, node }) {
      const state = useMarkdownRender();
      const start = mdPosition(node, state.changedRanges)?.["data-md-start"];
      if (isLeadingH1(state.sourceMarkdown, start)) {
        if (state.hideLeadingHeading) return null;
        if (state.version != null) {
          return (
            <div className="mb-4 flex items-start justify-between gap-3">
              <h1 className="min-w-0 text-2xl font-semibold leading-tight">{children}</h1>
              <Badge variant="secondary" className="shrink-0 print:hidden">
                v{state.version}
              </Badge>
            </div>
          );
        }
      }
      return (
        <h1 className="mb-4 text-2xl font-semibold leading-tight">{children}</h1>
      );
    },
    h2: function MarkdownH2({ children, node }) {
      const options = useMarkdownRender();
      const heading = flattenText(children);
      const isInformationRegister = isTransmittalHeading(heading);
      const attributes = mdPosition(node, options.changedRanges);
      if (isInformationRegister) {
        const open = options.informationRegisterOpen ?? false;
        const displayHeading = displayTransmittalHeading(heading);
        return (
          <div className="mt-8 border-b pb-2 first:mt-0 print:break-before-page">
            <div className="flex min-h-11 items-center gap-2">
              <h2
                id={sectionAnchor(heading)}
                className="pmp-section-heading min-w-0 flex-1 text-lg font-semibold"
                {...attributes}
              >
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center gap-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring print:pointer-events-none"
                  aria-expanded={open}
                  aria-controls="project-documents-register"
                  onMouseDown={(event) => {
                    // Avoid focus-driven scroll jumps in the draft scrollport.
                    event.preventDefault();
                  }}
                  onClick={(event) => {
                    event.preventDefault();
                    options.onToggleInformationRegister?.();
                  }}
                >
                  <ChevronRight
                    className={[
                      "size-4 shrink-0 transition-transform",
                      open ? "rotate-90" : "",
                    ].join(" ")}
                    aria-hidden
                  />
                  <span>{displayHeading}</span>
                </button>
              </h2>
              {options.canLoadTransmittal && options.onLoadTransmittal ? (
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  className="shrink-0 print:hidden"
                  disabled={options.isSavingTransmittal}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    options.onLoadTransmittal?.();
                  }}
                >
                  Load Transmittal
                </Button>
              ) : null}
              {options.canSaveTransmittal && options.onSaveTransmittal ? (
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  className="shrink-0 print:hidden"
                  disabled={options.isSavingTransmittal}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    options.onSaveTransmittal?.();
                  }}
                >
                  {options.isSavingTransmittal ? (
                    <LoaderCircle className="size-3.5 animate-spin" aria-hidden />
                  ) : null}
                  {options.isSavingTransmittal ? "Saving…" : "Save Transmittal"}
                </Button>
              ) : null}
            </div>
            {options.transmittalSaveError ? (
              <p className="mt-2 text-xs text-destructive print:hidden" role="alert">
                {options.transmittalSaveError}
              </p>
            ) : null}
          </div>
        );
      }
      return (
        <div className="mt-8 flex min-h-8 items-center gap-2 border-b pb-2 first:mt-0">
          <h2
            id={sectionAnchor(heading)}
            className="pmp-section-heading min-w-0 text-lg font-semibold"
            {...attributes}
          >
            {children}
          </h2>
        </div>
      );
    },
  };
}

const MARKDOWN_COMPONENTS = markdownComponents();

function flattenText(children: ReactNode): string {
  if (typeof children === "string") return children;
  if (Array.isArray(children)) return children.map(flattenText).join("");
  if (typeof children === "object" && children !== null && "props" in children) {
    const props = children.props as { children?: ReactNode };
    return flattenText(props.children);
  }
  return "";
}

function blockLabel(type: ArtifactBlockTarget["type"]): string {
  return type === "table_row"
    ? "table row"
    : type === "list_item"
      ? "list item"
      : "paragraph";
}

function headerLabelsFromTable(children: ReactNode): string[] {
  for (const section of Children.toArray(children)) {
    if (!isValidElement<{ children?: ReactNode }>(section)) continue;
    for (const row of Children.toArray(section.props.children)) {
      if (!isValidElement<{ children?: ReactNode }>(row)) continue;
      const cells = Children.toArray(row.props.children);
      if (!cells.length) continue;
      return cells.map((cell) =>
        isValidElement<{ children?: ReactNode }>(cell)
          ? flattenText(cell.props.children).trim()
          : flattenText(cell).trim(),
      );
    }
  }
  return [];
}

function informationRegisterTable(children: ReactNode): boolean {
  const text = flattenText(children).toLowerCase();
  return (
    text.includes("document number") &&
    text.includes("title") &&
    text.includes("rev") &&
    text.includes("category")
  );
}

function consultantsTableLayout(
  children: ReactNode,
): { dropColumnIndex: number | null; feeColumnIndex: number } | null {
  const text = flattenText(children).toLowerCase();
  if (
    !(
      text.includes("discipline") &&
      text.includes("firm") &&
      text.includes("fee") &&
      text.includes("status") &&
      text.includes("citation")
    )
  ) {
    return null;
  }
  // Legacy appointment register kept Scope / services at column index 2.
  const hasScope =
    text.includes("scope / services") || text.includes("scope/services");
  return {
    dropColumnIndex: hasScope ? 2 : null,
    // After dropping scope, Fee is always column index 2.
    feeColumnIndex: 2,
  };
}

const EMPTY_TABLE_LAYOUT: PmpTableLayout = {
  blankFeeNotEvidenced: false,
  dropColumnIndexes: [],
  feeColumnIndex: null,
  renameHeaders: {},
  isFfe: false,
  finishColumnIndex: null,
  commentColumnIndex: null,
  citationColumnIndex: null,
  appendCitation: false,
  blankCitationHeader: false,
  ffeLayout: null,
};

function tableLayoutFor(
  headers: readonly string[],
  consultantsLayout: { dropColumnIndex: number | null; feeColumnIndex: number } | null,
  ffeLayout: FfeTableLayout | null,
): PmpTableLayout {
  if (consultantsLayout) {
    return {
      ...EMPTY_TABLE_LAYOUT,
      blankFeeNotEvidenced: true,
      dropColumnIndexes:
        consultantsLayout.dropColumnIndex === null
          ? []
          : [consultantsLayout.dropColumnIndex],
      feeColumnIndex: consultantsLayout.feeColumnIndex,
    };
  }
  if (ffeLayout) {
    return {
      ...EMPTY_TABLE_LAYOUT,
      dropColumnIndexes: ffeLayout.dropColumnIndexes,
      renameHeaders: ffeLayout.renameHeaders,
      isFfe: true,
      finishColumnIndex: ffeLayout.finishColumnIndex,
      commentColumnIndex: ffeLayout.commentColumnIndex,
      citationColumnIndex: ffeLayout.citationColumnIndex,
      appendCitation: ffeLayout.appendCitation,
      blankCitationHeader: ffeLayout.blankCitationHeader,
      ffeLayout,
    };
  }
  const register: RegisterCitationLayout | null =
    briefTableLayoutFromHeaders(headers) ??
    pmpRegisterTableLayoutFromHeaders(headers);
  if (!register) return EMPTY_TABLE_LAYOUT;
  return {
    ...EMPTY_TABLE_LAYOUT,
    dropColumnIndexes: register.dropColumnIndexes,
    citationColumnIndex: register.citationColumnIndex,
    appendCitation: register.appendCitation,
    blankCitationHeader: register.blankCitationHeader,
  };
}

function harvestRowCitations(cells: readonly ReactNode[]): string {
  return extractCitationTokens(cells.map((cell) => flattenText(cell)).join(" "));
}

function citationDisplayValue(text: string): string {
  const trimmed = text.trim();
  if (!isCitationCellValue(trimmed) || trimmed === "—" || trimmed === "-" || trimmed === "–") {
    return extractCitationTokens(trimmed);
  }
  return extractCitationTokens(trimmed) || trimmed;
}

function appendTrailingCell(template: ReactNode, content: ReactNode): ReactNode {
  if (!isValidElement<{ children?: ReactNode }>(template)) {
    return (
      <td key="citation-col" className="border-b px-3 py-2 align-middle text-foreground">
        {content}
      </td>
    );
  }
  return cloneElement(template, { key: "citation-col" }, content);
}

function rangesEqual(
  left: MarkdownRange | null | undefined,
  right: MarkdownRange | null | undefined,
): boolean {
  return Boolean(left && right && left.start === right.start && left.end === right.end);
}

function isPmpGovernanceDisclaimer(value: string): boolean {
  const normalized = value.toLowerCase().replace("owner-side", "owner side");
  return (
    normalized.includes("owner side review and governance plan") &&
    normalized.includes("not an instruction") &&
    normalized.includes("statutory submission") &&
    normalized.includes("construction management plan")
  );
}

function stripOwnerBriefLeadIn(value: string): string {
  return value.replace(
    /^\s*draft owner project brief\s*(?:—|–|-|:)\s*formal sign[- ]off pending\.?\s*/i,
    "",
  );
}

function sectionAnchor(heading: string): string {
  return heading.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function citationBadgeClassName(conflicted: boolean): string {
  return conflicted
    ? "evidence-status-chip border-[color-mix(in_oklch,var(--sw-critical)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-critical)_14%,transparent)] text-[var(--sw-critical)]"
    : "evidence-status-chip border-transparent bg-[var(--decision-evidenced-bg)] text-[var(--decision-evidenced-text)]";
}

function renderEvidenceCell(
  children: ReactNode,
  options?: { conflicted?: boolean },
): ReactNode {
  const text = flattenText(children).trim();
  let cleaned = stripEvidenceOnFileLabel(stripUserProvidedLabel(text));
  cleaned = stripRequiringResolution(cleaned);
  cleaned = stripConfirmedPrefix(cleaned);
  if (/^conflict\b/i.test(cleaned)) {
    return "";
  }
  if (cleaned !== text && !cleaned) return "—";
  if (/^\[\d+\](?:\s+\[\d+\])*$/.test(cleaned)) {
    const tokens = cleaned.split(/\s+/);
    if (tokens.length === 1) {
      return (
        <Badge
          variant="outline"
          className={citationBadgeClassName(Boolean(options?.conflicted))}
        >
          {cleaned}
        </Badge>
      );
    }
    return (
      <span className="inline-flex flex-wrap items-center gap-1">
        {tokens.map((token) => (
          <Badge
            key={token}
            variant="outline"
            className={citationBadgeClassName(Boolean(options?.conflicted))}
          >
            {token}
          </Badge>
        ))}
      </span>
    );
  }
  const match = EVIDENCE_STATUSES.find(
    (status) =>
      status !== "Conflict" &&
      (cleaned === status ||
        cleaned.startsWith(`${status} `) ||
        cleaned.includes(` / ${status}`)),
  );
  if (!match) {
    if (cleaned !== text) return cleaned || "—";
    return children;
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <Badge
        variant="outline"
        className={evidenceBadgeClassName(match)}
      >
        <span data-status-dot={evidenceStatusDot(match)} aria-hidden />
        {match}
      </Badge>
      {cleaned !== match ? <span>{cleaned.replace(match, "").trim()}</span> : null}
    </span>
  );
}

function rowHasConflict(children: ReactNode): boolean {
  return Children.toArray(children).some((cell) => {
    const text = flattenText(cell).trim();
    return (
      /^conflict\b/i.test(text) ||
      /\brequiring resolution\b/i.test(text) ||
      /\bconflict:\b/i.test(text)
    );
  });
}

function normalizeSummaryRow(children: ReactNode, projectTitle?: string): ReactNode {
  const cells = Children.toArray(children);
  if (cells.length < 2) return children;
  const label = flattenText(cells[0]).trim().toLowerCase().replace(/\s+/g, " ");
  const citation = flattenText(cells.at(-1)).trim();
  if (citation && !/^(?:\[\d+\]|\u2014|-)$/.test(citation)) return children;
  const originalDetail = stripConfirmedPrefix(
    stripEvidenceOnFileLabel(stripUserProvidedLabel(flattenText(cells[1]).trim())),
  );
  const legacyDescription =
    ["project", "project title"].includes(label) &&
    Boolean(projectTitle) &&
    originalDetail.toLowerCase() !== projectTitle?.trim().toLowerCase();
  const isProject = ["project", "project title"].includes(label) && !legacyDescription;
  const isOwner = [
    "client / owner",
    "client/owner",
    "owners",
    "owner",
    "client",
  ].includes(label);
  const isAddress = [
    "site / asset",
    "site/asset",
    "site / address",
    "address",
  ].includes(label);
  const isDescription =
    ["description", "project description"].includes(label) || legacyDescription;
  if (!isProject && !isOwner && !isAddress && !isDescription) return children;

  return cells.map((cell, index) => {
    if (!isValidElement<{ children?: ReactNode }>(cell)) return cell;
    if (index === 0) {
      let normalizedLabel = "Description";
      if (isProject) normalizedLabel = "Project";
      else if (isOwner) normalizedLabel = "Owner";
      else if (isAddress) normalizedLabel = "Address";
      return cloneElement(cell, undefined, normalizedLabel);
    }
    if (index === cells.length - 1) {
      if (isProject || legacyDescription || citation === "—" || citation === "-") {
        return cloneElement(cell, undefined, "");
      }
      return cell;
    }
    if (index !== 1) return cell;
    const detail = isProject && projectTitle ? projectTitle : originalDetail;
    const cleaned = isOwner
      ? stripProposalAddressee(detail)
      : isAddress
        ? summaryAddressDetail(detail)
        : detail;
    return cloneElement(cell, undefined, cleaned);
  });
}

function normalizeSummaryTable(children: ReactNode, projectTitle?: string): ReactNode {
  const tableChildren = Children.toArray(children);
  const desiredOrder = ["project", "address", "owner", "description"];
  const collectedRows: ReactNode[] = [];

  for (const tableChild of tableChildren) {
    if (!isValidElement<{ children?: ReactNode }>(tableChild)) continue;
    for (const row of Children.toArray(tableChild.props.children)) {
      const label = summaryLabelFromRow(row);
      if (label === "critical current position" || label === "field") continue;
      if (isCombinedIdentityLabel(label)) {
        collectedRows.push(...expandCombinedIdentityRow(row, projectTitle));
        continue;
      }
      collectedRows.push(row);
    }
  }

  // Drop non-table bridge content: identity summary is rows only.
  const rowKinds = collectedRows.map((row) => summaryRowKind(row, projectTitle));
  const identityKinds = desiredOrder.slice(0, 3);
  const isIdentitySummary =
    rowKinds.includes("address") &&
    rowKinds.includes("owner") &&
    (rowKinds.includes("project") ||
      rowKinds.includes("description") ||
      Boolean(projectTitle));

  if (!isIdentitySummary) {
    // Keep ordinary thead/tbody structure; only drop review-only rows.
    return tableChildren.map((tableChild) => {
      if (!isValidElement<{ children?: ReactNode }>(tableChild)) return tableChild;
      const rows = Children.toArray(tableChild.props.children).filter((row) => {
        const label = summaryLabelFromRow(row);
        return label !== "critical current position" && label !== "field";
      });
      return cloneElement(tableChild, undefined, rows);
    });
  }

  const bodyRows = collectedRows.map((row, index) =>
    asSummaryBodyRow(row, index),
  );
  const bodyKinds = bodyRows.map((row) => summaryRowKind(row, projectTitle));
  const rowsByKind = new Map<string, ReactNode>();
  bodyKinds.forEach((kind, index) => {
    if (!kind || rowsByKind.has(kind)) return;
    rowsByKind.set(kind, bodyRows[index]);
  });
  if (!rowsByKind.has("project") && projectTitle) {
    rowsByKind.set("project", summaryProjectRow(projectTitle));
  }
  const orderedKinds = desiredOrder.filter((kind) => rowsByKind.has(kind));
  if (!identityKinds.every((kind) => rowsByKind.has(kind))) {
    return <tbody key="summary-body">{bodyRows}</tbody>;
  }
  const knownRows = new Set(rowsByKind.values());
  const otherRows = bodyRows.filter((row) => !knownRows.has(row));
  // Extra user/AI rows must keep document order; appending them after the
  // identity quartet made freshly inserted rows jump to the table bottom.
  if (otherRows.length > 0) {
    return <tbody key="summary-body">{bodyRows}</tbody>;
  }
  const orderedRows = orderedKinds.map((kind) => rowsByKind.get(kind) as ReactNode);
  return (
    <tbody key="summary-body">{orderedRows}</tbody>
  );
}

function isCombinedIdentityLabel(label: string): boolean {
  return /^project\s*\/\s*(?:owners?|clients?)\s*\/\s*(?:site|address)$/i.test(label);
}

function expandCombinedIdentityRow(
  row: ReactNode,
  projectTitle?: string,
): ReactNode[] {
  if (!isValidElement<{ children?: ReactNode }>(row)) return [row];
  const cells = Children.toArray(row.props.children);
  if (cells.length < 2) return [row];
  const detail = stripConfirmedPrefix(flattenText(cells[1]).trim());
  const citation = flattenText(cells.at(-1)).trim();
  const citationValue = /^(?:\[\d+\]|\u2014|-)?$/.test(citation) ? citation : "";
  const parts = detail.split(/\s*\/\s*/).map((part) => stripConfirmedPrefix(part.trim()));
  while (parts.length < 3) parts.push("");
  const projectValue = projectTitle || parts[0];
  return [
    summaryIdentityRow("Project", projectValue, "", "combined-project"),
    summaryIdentityRow("Address", parts[2], citationValue, "combined-address"),
    summaryIdentityRow("Owner", parts[1], citationValue, "combined-owner"),
  ];
}

function summaryIdentityRow(
  label: string,
  detail: string,
  citation: string,
  key: string,
): ReactNode {
  return (
    <tr key={key} className="sw-table-row even:bg-muted/20">
      <td className="border-b px-3 py-2 align-top text-foreground">{label}</td>
      <td className="border-b px-3 py-2 align-top text-foreground">{detail}</td>
      <td className="border-b px-3 py-2 align-top text-foreground">{citation}</td>
    </tr>
  );
}

function asSummaryBodyRow(
  row: ReactNode,
  index: number,
): ReactNode {
  if (!isValidElement<{ children?: ReactNode }>(row)) return row;
  // Keep the original row element (offsets, double-click, activate) while forcing
  // body cells to `td` — GFM identity headers otherwise stay as `th`.
  const cells = Children.toArray(row.props.children).map((cell, cellIndex) => {
    if (!isValidElement<{ children?: ReactNode }>(cell)) return cell;
    if (typeof cell.type === "string" && cell.type.toLowerCase() === "td") {
      return cell;
    }
    return (
      <td
        key={cell.key ?? `summary-cell-${index}-${cellIndex}`}
        className="border-b px-3 py-2 align-top text-foreground"
      >
        {cell.props.children}
      </td>
    );
  });
  return cloneElement(row, { key: `summary-row-${index}` }, cells);
}

function summaryRowKind(row: ReactNode, projectTitle?: string): string | null {
  if (!isValidElement<{ children?: ReactNode }>(row)) return null;
  const cells = Children.toArray(row.props.children);
  if (!cells.length) return null;
  const label = flattenText(cells[0]).trim().toLowerCase().replace(/\s+/g, " ");
  if (
    ["site / asset", "site/asset", "site / address", "site", "address"].includes(
      label,
    )
  ) {
    return "address";
  }
  if (
    ["client / owner", "client/owner", "owners", "owner", "client"].includes(label)
  ) {
    return "owner";
  }
  if (["project", "project title"].includes(label)) {
    const detail = stripConfirmedPrefix(
      stripUserProvidedLabel(flattenText(cells[1]).trim()),
    );
    return projectTitle && detail.toLowerCase() !== projectTitle.trim().toLowerCase()
      ? "description"
      : "project";
  }
  return ["description", "project description"].includes(label) ? "description" : null;
}

function summaryLabel(node: ReactNode): string {
  return flattenText(node).trim().toLowerCase().replace(/\s+/g, " ");
}

function summaryLabelFromRow(row: ReactNode): string {
  if (!isValidElement<{ children?: ReactNode }>(row)) return "";
  return summaryLabel(Children.toArray(row.props.children)[0]);
}

function summaryProjectRow(projectTitle: string): ReactNode {
  return (
    <tr key="project-profile-title" className="sw-table-row even:bg-muted/20">
      <td className="border-b px-3 py-2 align-top text-foreground">Project</td>
      <td className="border-b px-3 py-2 align-top text-foreground">{projectTitle}</td>
      <td className="border-b px-3 py-2 align-top text-foreground" />
    </tr>
  );
}

function stripProposalAddressee(value: string): string {
  return value
    .replace(/\s*(?:\.\s*)?proposal addressed to\s+[^.]+\.?/gi, "")
    .replace(/[.\s]+$/, "");
}

function stripUserProvidedLabel(value: string): string {
  if (
    /^\s*\*{0,2}user[- ]provided\*{0,2}(?:\s*\/\s*(?:assumption|not evidenced))?\.?\s*$/i.test(
      value,
    )
  ) {
    return "—";
  }
  return value
    .replace(
      /\s*(?:\u2014|\u2013|-|\/|;|,)\s*(?:is\s+)?\*{0,2}user[- ]provided\*{0,2}(?:\s*\/\s*(?:assumption|not evidenced))?\.?/gi,
      "",
    )
    .replace(/(:\s*)\*{0,2}user[- ]provided\*{0,2}\s*/gi, "$1")
    .replace(/\s*,?\s*is\s+\*{0,2}user[- ]provided\*{0,2}\.?/gi, "")
    .trim();
}

function stripEvidenceOnFileLabel(value: string): string {
  if (/^\s*\*{0,2}evidence on file\*{0,2}\s*:?\s*\*{0,2}\s*\.?\s*$/i.test(value)) {
    return "";
  }
  return value
    .replace(/^\s*\*{0,2}evidence on file\*{0,2}\s*:\s*\*{0,2}\s*/i, "")
    .replace(
      /\s*(?:(?:\u2014|\u2013|-|\/|;|,)\s*)?\*{0,2}\bevidence on file\b\*{0,2}\s*:?\s*\*{0,2}\s*\.?/gi,
      "",
    )
    .trim();
}

function stripConfirmedPrefix(value: string): string {
  return value.replace(/^\s*\*?confirmed\b[:\s,\u2014\u2013-]*/i, "").trim();
}

function stripRequiringResolution(value: string): string {
  return value.replace(/\s*(?:,\s*)?\brequiring resolution\b\.?/gi, "").trim();
}

/** Blank non-table Project Summary prose so offsets stay aligned for selection. */
function blankProjectSummaryProse(markdown: string): string {
  const lines = markdown.split("\n");
  const out: string[] = [];
  let inSummary = false;
  let inCitationKey = false;
  let skippingCoverageRegister = false;
  let skippingCitationTable = false;
  for (const line of lines) {
    const trimmed = line.trim();
    if (/^#{2,3}\s+/.test(trimmed)) {
      const heading = trimmed.replace(/^#{2,3}\s+/, "").trim();
      const isH2 = /^##\s+/.test(trimmed);
      if (isH2) {
        skippingCoverageRegister = /evidence coverage register/i.test(heading);
        inSummary = /^project summary$/i.test(heading);
      }
      inCitationKey = /^citation key$/i.test(heading);
      skippingCitationTable = false;
      if (isH2 && skippingCoverageRegister) {
        out.push(" ".repeat(line.length));
        continue;
      }
      out.push(line);
      continue;
    }
    if (skippingCoverageRegister) {
      out.push(" ".repeat(line.length));
      continue;
    }
    if (inSummary && trimmed && !trimmed.startsWith("|")) {
      out.push(" ".repeat(line.length));
      continue;
    }
    if (inCitationKey) {
      if (/^\|\s*section\s*\|\s*evidence status\s*\|\s*(?:citation|ref)\s*\|$/i.test(trimmed)) {
        skippingCitationTable = true;
        out.push(" ".repeat(line.length));
        continue;
      }
      if (skippingCitationTable) {
        if (trimmed.startsWith("|")) {
          out.push(" ".repeat(line.length));
          continue;
        }
        skippingCitationTable = false;
      }
      if (/^\*\*documents cited:\*\*$/i.test(trimmed) || /^documents cited:$/i.test(trimmed)) {
        out.push(" ".repeat(line.length));
        continue;
      }
      // Bare "[n] doc — status" lines collapse into one paragraph in CommonMark;
      // promote them to list items so each citation key sits on its own row.
      const citationEntry = trimmed.match(/^(?:[-*+]\s+)?(\[\d+\]\s+.+)$/);
      if (citationEntry && !/^[-*+]\s+/.test(trimmed)) {
        const indent = line.match(/^\s*/)?.[0] ?? "";
        out.push(`${indent}- ${citationEntry[1]}`);
        continue;
      }
    }
    out.push(line);
  }
  return out.join("\n");
}

function summaryAddressDetail(detail: string): string {
  const withoutScope = detail
    .split(/(?<=\.)\s+/)
    .filter((sentence) => {
      const normalized = sentence.toLowerCase();
      return (
        !normalized.includes("upper metal roof") &&
        !normalized.includes("stormwater drainage")
      );
    })
    .join(" ")
    .trim();
  return stripConfirmedPrefix(withoutScope.replace(/[.\s]+$/, ""));
}

function evidenceStatusDot(
  status: (typeof EVIDENCE_STATUSES)[number],
): "positive" | "caution" | "critical" | "info" | "quiet" {
  switch (status) {
    case "Grounded":
      return "positive";
    case "Conflict":
      return "critical";
    case "Confirm":
    case "Partial":
    case "Assumption":
    case "Gap":
    case "Not evidenced":
      return "caution";
    case "Profile":
      return "info";
    default:
      return "quiet";
  }
}

function evidenceBadgeClassName(status: (typeof EVIDENCE_STATUSES)[number]): string {
  switch (status) {
    case "Grounded":
      return "evidence-status-chip border-transparent bg-[var(--decision-evidenced-bg)] text-[var(--decision-evidenced-text)]";
    case "Partial":
    case "Assumption":
    case "Profile":
      return "evidence-status-chip border-transparent bg-[var(--decision-assumed-bg)] text-[var(--decision-assumed-text)]";
    case "Confirm":
    case "Gap":
    case "Not evidenced":
      return "evidence-status-chip border-[color-mix(in_oklch,var(--sw-caution)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-caution)_14%,transparent)] text-[var(--sw-caution)]";
    case "Conflict":
      return "evidence-status-chip border-[color-mix(in_oklch,var(--sw-critical)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-critical)_14%,transparent)] text-[var(--sw-critical)]";
    default:
      return "evidence-status-chip";
  }
}

export function MarkdownContent({
  markdown,
  version,
  hideLeadingHeading = false,
  projectId,
  decisions,
  projectTitle,
  readOnly = false,
  changedRanges,
  showChanges = false,
  showTraceQa = true,
  containerRef,
  onDraftUpdated,
  editingRange,
  editingFocusCellIndex,
  editingCaretPoint = null,
  isSavingEdit = false,
  editError,
  blockComposer = null,
  isSavingBlockComposer = false,
  onEditSelection,
  onEditWithAi,
  onCancelSelectionEdit,
  onSaveSelectionEdit,
  onCancelBlockComposer,
  onSaveBlockComposer,
  onMutateBlock,
  protectedBlockIds,
  reviewBlockStatuses,
  onLoadTransmittal,
  canLoadTransmittal = false,
  onSaveTransmittal,
  canSaveTransmittal = false,
  isSavingTransmittal = false,
  transmittalSaveError = null,
}: {
  /**
   * Already normalized (see `normalizeDraftMarkdown`). Callers own the
   * transform so that the offsets stamped here and the offsets a caller slices
   * with are the same space — design decision D3.
   */
  markdown: string;
  version?: number;
  hideLeadingHeading?: boolean;
  projectId?: string;
  decisions?: ProjectDecision[];
  projectTitle?: string;
  readOnly?: boolean;
  changedRanges?: readonly MarkdownRange[];
  showChanges?: boolean;
  showTraceQa?: boolean;
  containerRef?: React.Ref<HTMLDivElement>;
  onDraftUpdated?: (draft: DraftArtifact) => void;
  onLoadTransmittal?: () => void;
  canLoadTransmittal?: boolean;
  onSaveTransmittal?: () => void;
  canSaveTransmittal?: boolean;
  isSavingTransmittal?: boolean;
  transmittalSaveError?: string | null;
  editingRange?: MarkdownRange | null;
  editingFocusCellIndex?: number;
  editingCaretPoint?: { x: number; y: number } | null;
  isSavingEdit?: boolean;
  editError?: string | null;
  blockComposer?: ArtifactBlockComposerState | null;
  isSavingBlockComposer?: boolean;
  onEditSelection?: InlineEditOptions["onEditSelection"];
  onEditWithAi?: (range: MarkdownRange, rect: DOMRect) => void;
  onCancelSelectionEdit?: () => void;
  onSaveSelectionEdit?: (range: MarkdownRange, markdown: string) => Promise<void>;
  onCancelBlockComposer?: () => void;
  onSaveBlockComposer?: (content: string) => void;
  onMutateBlock?: InlineEditOptions["onMutateBlock"];
  protectedBlockIds?: Set<string>;
  reviewBlockStatuses?: Map<string, "conflict" | "propose_delete">;
}) {
  const [informationRegisterOpen, setInformationRegisterOpen] = useState(false);
  const traceQa = useMemo(() => splitTraceQa(markdown), [markdown]);
  const presented = useMemo(() => {
    const grouped = groupConsecutiveDecisionFences(
      blankProjectSummaryProse(maskArtifactBlockMarkers(traceQa.primary)),
    );
    return foldFfeScheduleDecisions(grouped);
  }, [traceQa.primary]);
  const presentedPrimary = presented.markdown;
  const foldedDecisionsById = presented.foldedById;
  const sections = useMemo(
    () => splitMarkdownSections(presentedPrimary),
    [presentedPrimary],
  );
  const sourceSections = useMemo(
    () => splitMarkdownSections(traceQa.primary),
    [traceQa.primary],
  );
  const activeRanges = useMemo(
    () => (showChanges ? (changedRanges ?? []) : []),
    [showChanges, changedRanges],
  );
  const decisionsById = useMemo(
    () =>
      decisions
        ? new Map(decisions.map((decision) => [decision.decision_id, decision]))
        : undefined,
    [decisions],
  );
  const renderState = useMemo<MarkdownRenderState>(
    () => ({
      version,
      hideLeadingHeading,
      changedRanges: activeRanges,
      projectTitle,
      projectId,
      decisionsById,
      foldedDecisionsById,
      readOnly,
      onDraftUpdated,
      sourceMarkdown: traceQa.primary,
      renderedMarkdown: presentedPrimary,
      sourceSections,
      editingRange,
      editingFocusCellIndex,
      isSavingEdit,
      editError,
      blockComposer,
      isSavingBlockComposer,
      editingCaretPoint,
      onEditSelection,
      onEditWithAi,
      onCancelSelectionEdit,
      onSaveSelectionEdit,
      onCancelBlockComposer,
      onSaveBlockComposer,
      onMutateBlock,
      protectedBlockIds,
      reviewBlockStatuses,
      informationRegisterOpen,
      onToggleInformationRegister: () =>
        setInformationRegisterOpen((current) => !current),
      onLoadTransmittal: onLoadTransmittal
        ? () => {
            setInformationRegisterOpen(true);
            onLoadTransmittal();
          }
        : undefined,
      canLoadTransmittal,
      onSaveTransmittal: onSaveTransmittal
        ? () => {
            setInformationRegisterOpen(true);
            onSaveTransmittal();
          }
        : undefined,
      canSaveTransmittal,
      isSavingTransmittal,
      transmittalSaveError,
    }),
    [
      version,
      hideLeadingHeading,
      activeRanges,
      projectTitle,
      projectId,
      decisionsById,
      foldedDecisionsById,
      readOnly,
      onDraftUpdated,
      traceQa.primary,
      presentedPrimary,
      sourceSections,
      editingRange,
      editingFocusCellIndex,
      isSavingEdit,
      editError,
      blockComposer,
      isSavingBlockComposer,
      editingCaretPoint,
      onEditSelection,
      onEditWithAi,
      onCancelSelectionEdit,
      onSaveSelectionEdit,
      onCancelBlockComposer,
      onSaveBlockComposer,
      onMutateBlock,
      protectedBlockIds,
      reviewBlockStatuses,
      informationRegisterOpen,
      onLoadTransmittal,
      canLoadTransmittal,
      onSaveTransmittal,
      canSaveTransmittal,
      isSavingTransmittal,
      transmittalSaveError,
    ],
  );

  return (
    <div
      ref={containerRef}
      className="draft-markdown text-sm text-foreground"
      data-project-title={projectTitle}
      data-draft-version={version}
    >
      <div className="flex gap-6">
        {sections.length > 1 ? (
          <nav
            aria-label="Document sections"
            className="sticky top-4 hidden h-fit w-28 shrink-0 lg:block print:hidden"
          >
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Sections
            </p>
            <ul className="space-y-1 text-xs">
              {sections.map((section) => (
                <li key={section.heading}>
                  <a
                    className="block px-1.5 py-1 leading-snug text-muted-foreground hover:bg-muted hover:text-foreground"
                    href={`#${sectionAnchor(section.heading)}`}
                  >
                    {section.heading}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}
        <div className="min-w-0 flex-1">
          <FfeDecisionRenderContext.Provider
            value={{
              projectId,
              decisionsById,
              foldedDecisionsById,
              readOnly,
              onDraftUpdated,
            }}
          >
          <MarkdownRenderContext.Provider value={renderState}>
          <BlockActionsProvider>
          <ReactMarkdown
            remarkPlugins={REMARK_PLUGINS}
            components={MARKDOWN_COMPONENTS}
          >

            {presentedPrimary}
          </ReactMarkdown>
          </BlockActionsProvider>
          </MarkdownRenderContext.Provider>
          </FfeDecisionRenderContext.Provider>
          {showTraceQa && traceQa.qa ? (
            <details className="trace-qa mt-10 border-t border-[var(--sw-edge)] pt-4 print:hidden">
              <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-4 font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <span>Trace &amp; QA</span>
                <span className="font-mono text-xs uppercase tracking-[0.12em]">Review only</span>
              </summary>
              <div className="mt-3 border border-[var(--sw-edge)] bg-[var(--sw-panel)] p-4 text-muted-foreground">
                <ReactMarkdown
                  remarkPlugins={REMARK_PLUGINS}
                  components={MARKDOWN_COMPONENTS}
                >
                  {maskArtifactBlockMarkers(traceQa.qa)}
                </ReactMarkdown>
              </div>
            </details>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function hydrateEmbeddedDecision(
  embedded: EmbeddedDecision,
  canonical: ProjectDecision | undefined,
): EmbeddedDecision {
  if (!canonical) return embedded;
  return {
    ...embedded,
    section: canonical.section || embedded.section,
    label: canonical.label || embedded.label,
    options: canonical.options.length ? canonical.options : embedded.options,
    selected: canonical.selected,
    source: canonical.source,
    revision: canonical.revision,
    set_revision: canonical.set_revision,
    evidence_conflict: canonical.evidence_conflict,
    agent_suggestion: canonical.agent_suggestion ?? undefined,
  };
}

function parseDecisionGroup(
  raw: string,
  decisionsById?: ReadonlyMap<string, ProjectDecision>,
): EmbeddedDecision[] {
  try {
    const payloads = JSON.parse(raw) as unknown;
    if (!Array.isArray(payloads)) return [];
    return payloads
      .map((payload) => {
        const embedded = parseEmbeddedDecision(
          typeof payload === "string" ? payload : JSON.stringify(payload),
        );
        if (!embedded) return null;
        return hydrateEmbeddedDecision(embedded, decisionsById?.get(embedded.id));
      })
      .filter((decision): decision is EmbeddedDecision => decision !== null);
  } catch {
    return [];
  }
}
