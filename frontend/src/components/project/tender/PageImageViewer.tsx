import { ImageOff, Minus, Plus } from "lucide-react";
import { useMemo, useState, type CSSProperties } from "react";

import { Button } from "@/components/ui/button";

import type { TenderPageEvidence } from "./evidence";

type NaturalSize = {
  width: number;
  height: number;
};

export function PageImageViewer({ evidence }: { evidence: TenderPageEvidence }) {
  const [zoom, setZoom] = useState(1);
  const [naturalSize, setNaturalSize] = useState<NaturalSize | null>(null);
  const overlayStyle = useMemo(
    () => (evidence.bbox ? bboxStyle(evidence.bbox, naturalSize) : null),
    [evidence.bbox, naturalSize],
  );

  return (
    <section className="flex min-h-0 flex-col rounded-md border bg-card shadow-sm">
      <header className="flex items-center justify-between gap-3 border-b px-3 py-3">
        <div className="min-w-0">
          <p className="cockpit-zone-title">Source page</p>
          <p className="mt-1 truncate text-xs text-muted-foreground">{pageLabel(evidence)}</p>
        </div>
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            title="Zoom out"
            onClick={() => setZoom((current) => Math.max(0.6, current - 0.1))}
          >
            <Minus className="size-3.5" aria-hidden />
          </Button>
          <span className="w-10 text-center text-xs tabular-nums text-muted-foreground">
            {Math.round(zoom * 100)}%
          </span>
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            title="Zoom in"
            onClick={() => setZoom((current) => Math.min(2.4, current + 0.1))}
          >
            <Plus className="size-3.5" aria-hidden />
          </Button>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-auto bg-muted/40 p-3">
        {evidence.imagePath ? (
          <div
            className="relative mx-auto w-fit origin-top"
            style={{ transform: `scale(${zoom})` }}
          >
            <img
              src={evidence.imagePath}
              alt={pageLabel(evidence)}
              className="max-h-none max-w-none rounded-sm border bg-background shadow-sm"
              draggable={false}
              onLoad={(event) => {
                setNaturalSize({
                  width: event.currentTarget.naturalWidth,
                  height: event.currentTarget.naturalHeight,
                });
              }}
            />
            {overlayStyle ? (
              <div
                className="pointer-events-none absolute rounded-[3px] border-2 border-primary bg-primary/20 shadow-[0_0_0_9999px_rgb(0_0_0/0.10)]"
                style={overlayStyle}
              />
            ) : null}
          </div>
        ) : (
          <div className="flex min-h-96 items-center justify-center rounded-md border border-dashed bg-background p-6 text-center">
            <div className="max-w-xs">
              <ImageOff className="mx-auto size-8 text-muted-foreground" aria-hidden />
              <p className="mt-3 text-sm font-medium">No page image available</p>
              <p className="mt-1 text-xs text-muted-foreground">
                This QA item has no image path in its evidence payload.
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function pageLabel(evidence: TenderPageEvidence): string {
  const bits = [
    evidence.label,
    evidence.pageNumber === null ? null : `page ${evidence.pageNumber}`,
  ];
  return bits.filter((bit): bit is string => bit !== null).join(" / ") || "Evidence";
}

function bboxStyle(
  bbox: NonNullable<TenderPageEvidence["bbox"]>,
  naturalSize: NaturalSize | null,
): CSSProperties | null {
  const maxCoord = Math.max(bbox.x0, bbox.y0, bbox.x1, bbox.y1);
  const normalized = maxCoord <= 1;
  if (!normalized && (!naturalSize || naturalSize.width <= 0 || naturalSize.height <= 0)) {
    return null;
  }

  const pageWidth = normalized ? 1 : naturalSize!.width;
  const pageHeight = normalized ? 1 : naturalSize!.height;
  return {
    left: `${clampPercent((bbox.x0 / pageWidth) * 100)}%`,
    top: `${clampPercent((bbox.y0 / pageHeight) * 100)}%`,
    width: `${clampPercent(((bbox.x1 - bbox.x0) / pageWidth) * 100)}%`,
    height: `${clampPercent(((bbox.y1 - bbox.y0) / pageHeight) * 100)}%`,
  };
}

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, value));
}
