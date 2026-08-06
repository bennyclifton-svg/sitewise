import { User } from "lucide-react";
import { useEffect, useState } from "react";

import { supabase } from "@/lib/supabase";
import { cn } from "@/lib/utils";

function userDisplayName(email: string | null): string {
  if (!email) return "Loading…";
  const local = email.split("@")[0] ?? email;
  return local.replace(/[._-]+/g, " ").trim() || email;
}

function userInitials(email: string | null): string | null {
  if (!email) return null;
  const local = email.split("@")[0] ?? "";
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]?.[0] ?? ""}${parts[1]?.[0] ?? ""}`.toUpperCase();
  }
  return local.slice(0, 2).toUpperCase() || null;
}

export function AppSystemFooter({ className }: { className?: string }) {
  const [email, setEmail] = useState<string | null>(null);
  const initials = userInitials(email);

  useEffect(() => {
    let cancelled = false;

    void supabase.auth.getUser().then(({ data }) => {
      if (!cancelled) setEmail(data.user?.email ?? null);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!cancelled) setEmail(session?.user?.email ?? null);
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, []);

  return (
    <div
      className={cn(
        "app-system-footer flex shrink-0 items-center gap-2 border-t border-border bg-card px-3 py-2",
        className,
      )}
    >
      <div
        className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground"
        aria-hidden
      >
        {initials ? (
          <span className="text-[10px] font-semibold uppercase tracking-tight">
            {initials}
          </span>
        ) : (
          <User className="size-3.5" />
        )}
      </div>

      <span className="min-w-0 flex-1 truncate text-xs font-medium text-foreground">
        {userDisplayName(email)}
      </span>
    </div>
  );
}
