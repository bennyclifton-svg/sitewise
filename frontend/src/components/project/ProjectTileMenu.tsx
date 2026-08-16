import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function ProjectTileMenu({
  title,
  disabled,
  onRename,
  onDelete,
}: {
  title: string;
  disabled?: boolean;
  onRename?: () => void;
  onDelete: () => void;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          size="icon-xs"
          variant="ghost"
          disabled={disabled}
          aria-label={`Actions for ${title}`}
          title="Actions"
        >
          <MoreHorizontal className="size-4" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" sideOffset={4} className="min-w-[8rem]">
        {onRename ? (
          <DropdownMenuItem disabled={disabled} onSelect={onRename}>
            <Pencil className="size-3.5 shrink-0" aria-hidden />
            Rename
          </DropdownMenuItem>
        ) : null}
        <DropdownMenuItem
          variant="destructive"
          disabled={disabled}
          onSelect={onDelete}
        >
          <Trash2 className="size-3.5" aria-hidden />
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
