export function ProjectChatPreview() {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex shrink-0 items-center gap-2 border-b px-4 py-2">
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold">Clerk</h2>
          <p className="truncate text-xs text-muted-foreground">
            Preview only. Real chat opens inside a backend project cockpit.
          </p>
        </div>
      </header>
      <p className="px-4 py-3 text-sm text-muted-foreground">
        Connect the backend to use the project chat panel.
      </p>
    </div>
  );
}
