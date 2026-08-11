import { CreditCard, Globe, LogOut, Settings, User } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { signOut } from "@/lib/auth";
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
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="flex min-w-0 flex-1 items-center gap-2 rounded-sm text-left outline-none transition-colors hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Account menu"
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

            <Settings className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" side="top" className="min-w-[10rem]">
          <DropdownMenuItem asChild>
            <Link to="/billing">
              <CreditCard className="size-3.5" aria-hidden />
              Billing
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            {/* Static marketing page outside the SPA router — must be a full page load. */}
            <a href="/landing.html">
              <Globe className="size-3.5" aria-hidden />
              Landing page
            </a>
          </DropdownMenuItem>
          <DropdownMenuItem
            onSelect={() => {
              void signOut();
            }}
          >
            <LogOut className="size-3.5" aria-hidden />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
