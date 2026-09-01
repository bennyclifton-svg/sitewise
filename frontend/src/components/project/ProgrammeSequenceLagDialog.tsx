import { useState } from "react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function ProgrammeSequenceLagDialog({
  open,
  rowCount,
  linkCount,
  initialLag,
  onOpenChange,
  onApply,
}: {
  open: boolean;
  rowCount: number;
  linkCount: number;
  initialLag: number | null;
  onOpenChange: (open: boolean) => void;
  onApply: (lagDays: number) => void;
}) {
  const [lagDraft, setLagDraft] = useState(() =>
    initialLag === null ? "" : String(initialLag),
  );

  const parsedLag = Number(lagDraft);
  const valid = lagDraft.trim() !== "" && Number.isFinite(parsedLag) && parsedLag >= 0;

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/55" />
        <DialogPrimitive.Content className="sw-surface sw-contact fixed top-1/2 left-1/2 z-50 w-[calc(100vw-2rem)] max-w-sm -translate-x-1/2 -translate-y-1/2 p-4 text-[var(--sw-text-secondary)] outline-none">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <DialogPrimitive.Title className="text-sm font-medium text-[var(--sw-text-primary)]">
                Set sequence lag
              </DialogPrimitive.Title>
              <DialogPrimitive.Description className="mt-1 text-xs leading-5 text-[var(--sw-text-tertiary)]">
                Apply one lag to {linkCount} link{linkCount === 1 ? "" : "s"} across{" "}
                {rowCount} selected rows.
              </DialogPrimitive.Description>
            </div>
            <DialogPrimitive.Close asChild>
              <Button
                type="button"
                size="icon-xs"
                variant="ghost"
                aria-label="Close lag editor"
                className="rounded-sm text-[var(--sw-text-tertiary)] hover:text-[var(--sw-text-primary)]"
              >
                <X className="size-3.5" aria-hidden />
              </Button>
            </DialogPrimitive.Close>
          </div>
          <form
            className="mt-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (!valid) return;
              onApply(Math.round(parsedLag));
              onOpenChange(false);
            }}
          >
            <label className="text-xs font-medium text-[var(--sw-text-primary)]">
              Lag in days
              <Input
                autoFocus
                type="number"
                min={0}
                step={1}
                required
                value={lagDraft}
                placeholder={initialLag === null ? "Mixed" : undefined}
                aria-label="Sequence lag in days"
                className="mt-1.5 h-8 bg-[var(--sw-void)] text-sm tabular-nums"
                onChange={(event) => setLagDraft(event.target.value)}
              />
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <DialogPrimitive.Close asChild>
                <Button type="button" size="sm" variant="outline">
                  Cancel
                </Button>
              </DialogPrimitive.Close>
              <Button type="submit" size="sm" disabled={!valid}>
                Apply lag
              </Button>
            </div>
          </form>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
