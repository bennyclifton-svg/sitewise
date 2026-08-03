import type { ToolStatusEvent } from "@/lib/chat-events";

export type ToolActivityLine = {
  id: string;
  state: ToolStatusEvent["state"];
  label: string;
  detail?: string;
};

function basename(path: string): string {
  const trimmed = path.trim();
  if (!trimmed) return trimmed;
  const parts = trimmed.split(/[\\/]/);
  return parts[parts.length - 1] || trimmed;
}

function subjectFromEvent(event: ToolStatusEvent): string | null {
  if (event.documents && event.documents.length > 0) {
    const names = event.documents.map(basename).filter(Boolean);
    if (names.length === 0) return null;
    if (names.length === 1) return names[0];
    if (names.length === 2) return `${names[0]}, ${names[1]}`;
    return `${names[0]}, ${names[1]} +${names.length - 2} more`;
  }
  if (event.knowledgePath) return basename(event.knowledgePath);
  return null;
}

function detailForEvent(event: ToolStatusEvent): string {
  const parts = [event.message];
  if (event.percent !== undefined) {
    parts.push(`${Math.round(event.percent)}%`);
  }
  if (event.stage) {
    parts.push(`Stage: ${event.stage}`);
  }
  return parts.filter(Boolean).join(" · ");
}

/** Prefer the human message when it already carries a document subject. */
export function formatToolActivityLabel(event: ToolStatusEvent): string {
  const message = event.message.trim();
  if (message.includes(" · ")) return message;

  const subject = subjectFromEvent(event);
  if (subject) {
    const verb = message || (event.state === "running" ? "Working" : "Done");
    return `${verb} · ${subject}`;
  }

  if (message) return message;
  return event.tool.replaceAll("_", " ");
}

/**
 * Collapse streaming running/done pairs into one line per tool step so the
 * feed does not stack six identical chips for three searches.
 */
export function toolActivityLines(events: ToolStatusEvent[]): ToolActivityLine[] {
  const lines: ToolActivityLine[] = [];

  for (const [index, event] of events.entries()) {
    const label = formatToolActivityLabel(event);
    const previousEvent = index > 0 ? events[index - 1] : null;
    const previousLine = lines[lines.length - 1];

    if (
      previousLine &&
      previousEvent &&
      previousEvent.tool === event.tool &&
      previousEvent.state === "running" &&
      event.state !== "running"
    ) {
      previousLine.state = event.state;
      previousLine.label = label;
      previousLine.detail = detailForEvent(event);
      continue;
    }

    lines.push({
      id: `${event.tool}-${index}-${event.state}`,
      state: event.state,
      label,
      detail: detailForEvent(event),
    });
  }

  return lines;
}
