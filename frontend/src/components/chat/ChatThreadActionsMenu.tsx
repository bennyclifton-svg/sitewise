import { MoreHorizontal } from "lucide-react";
import { DropdownMenu } from "radix-ui";

import { Button } from "@/components/ui/button";

export function ChatThreadActionsMenu({
  title,
  onClose,
  onRename,
  onDelete,
}: {
  title: string;
  onClose: () => void;
  onRename: () => void;
  onDelete: () => void;
}) {
  return (
    <DropdownMenu.Root
      defaultOpen
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DropdownMenu.Trigger asChild>
        <Button
          type="button"
          size="icon-xs"
          variant="ghost"
          aria-label={`Actions for ${title}`}
          title="Actions"
          aria-expanded="true"
        >
          <MoreHorizontal className="size-3" aria-hidden />
        </Button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={4}
          collisionPadding={8}
          className="z-50 min-w-[6.5rem] rounded-md border bg-popover p-1 shadow-md outline-none"
        >
          <DropdownMenu.Item
            className="cursor-default rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-muted focus:bg-muted"
            onSelect={onRename}
          >
            Rename
          </DropdownMenu.Item>
          <DropdownMenu.Item
            className="cursor-default rounded-sm px-2 py-1.5 text-sm text-destructive outline-none hover:bg-muted focus:bg-muted"
            onSelect={onDelete}
          >
            Delete
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
