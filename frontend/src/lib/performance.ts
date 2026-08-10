const workflowStarts = new Set<string>();

export function markWorkflowStage(runId: string, stage: string): void {
  if (typeof performance === "undefined" || !runId || !stage) return;
  const start = `clerk:workflow:${runId}:start`;
  if (!workflowStarts.has(runId)) {
    performance.mark(start);
    workflowStarts.add(runId);
  }
  const mark = `clerk:workflow:${runId}:${stage}`;
  performance.mark(mark);
  if (stage === "scaffold_ready") measureOnce(`clerk:metric:ttfc:${runId}`, start, mark);
  if (stage === "section_completed") measureOnce(`clerk:metric:ttfu:${runId}`, start, mark);
  if (stage === "artefact_ready") measureOnce(`clerk:metric:complete:${runId}`, start, mark);
}

export function measureLocalMutation(name: string, startedAt: number): void {
  if (typeof performance === "undefined") return;
  performance.measure(`clerk:mutation:${name}`, {
    start: startedAt,
    end: performance.now(),
  });
}

function measureOnce(name: string, start: string, end: string): void {
  if (performance.getEntriesByName(name).length) return;
  try {
    performance.measure(name, start, end);
  } catch {
    // A browser may clear marks under memory pressure; metrics are advisory.
  }
}
