import {
  ArrowLeft,
  CreditCard,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type {
  BillingPlan,
  BillingPlansResponse,
  BillingStatus,
} from "@/lib/types/billing";

function formatError(error: unknown): string {
  return error instanceof ApiError ? error.message : "Billing is unavailable.";
}

export function BillingPage() {
  const [plans, setPlans] = useState<BillingPlansResponse | null>(null);
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyPlan, setBusyPlan] = useState<string | null>(null);
  const [portalBusy, setPortalBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadBilling() {
      setError(null);
      try {
        const [plansResponse, statusResponse] = await Promise.all([
          api.getBillingPlans(),
          api.getBillingStatus(),
        ]);
        if (!cancelled) {
          setPlans(plansResponse);
          setStatus(statusResponse);
        }
      } catch (loadError) {
        if (!cancelled) setError(formatError(loadError));
      }
    }

    void loadBilling();
    return () => {
      cancelled = true;
    };
  }, []);

  async function startCheckout(planId: string) {
    setBusyPlan(planId);
    setError(null);
    try {
      const checkoutUrl = await api.createBillingCheckout(planId);
      window.location.assign(checkoutUrl);
    } catch (checkoutError) {
      setError(formatError(checkoutError));
      setBusyPlan(null);
    }
  }

  async function openPortal() {
    setPortalBusy(true);
    setError(null);
    try {
      const portalUrl = await api.openBillingPortal();
      window.location.assign(portalUrl);
    } catch (portalError) {
      setError(formatError(portalError));
      setPortalBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-muted/20">
      <header className="border-b bg-background">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div className="min-w-0">
            <Button asChild variant="ghost" size="sm" className="-ml-2 mb-2">
              <Link to="/">
                <ArrowLeft className="size-4" aria-hidden />
                Cockpit
              </Link>
            </Button>
            <div className="flex items-center gap-2">
              <CreditCard className="size-5 text-muted-foreground" aria-hidden />
              <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
            </div>
          </div>
          {status ? (
            <Badge variant={status.read_only ? "outline" : "secondary"}>
              {status.subscription_status}
            </Badge>
          ) : null}
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-6xl gap-4 px-4 py-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <section className="space-y-4">
          {error ? (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
              {error}
            </div>
          ) : null}

          <div className="grid gap-3 md:grid-cols-2">
            {(plans?.plans ?? []).map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                currentPlanId={status?.current_plan_id}
                disabled={!plans?.billing_enabled || !plan.configured || busyPlan !== null}
                busy={busyPlan === plan.id}
                onCheckout={() => void startCheckout(plan.id)}
              />
            ))}
          </div>
        </section>

        <aside className="space-y-4">
          <section className="rounded-md border bg-background p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <ShieldCheck className="size-4" aria-hidden />
              Account
            </div>
            <dl className="mt-4 space-y-3 text-sm">
              <StatusRow label="Plan" value={status?.current_plan_id ?? "..."} />
              <StatusRow label="State" value={status?.subscription_status ?? "..."} />
              <StatusRow label="Mode" value={status?.environment ?? "..."} />
            </dl>
            <Button
              className="mt-4 w-full"
              variant="secondary"
              disabled={!status?.has_customer || portalBusy}
              onClick={() => void openPortal()}
            >
              <ExternalLink className="size-4" aria-hidden />
              {portalBusy ? "Opening..." : "Customer portal"}
            </Button>
          </section>
          {status?.quota ? <QuotaPanel quota={status.quota} /> : null}
        </aside>
      </main>
    </div>
  );
}

function PlanCard({
  plan,
  currentPlanId,
  disabled,
  busy,
  onCheckout,
}: {
  plan: BillingPlan;
  currentPlanId?: string;
  disabled: boolean;
  busy: boolean;
  onCheckout: () => void;
}) {
  const isCurrent = currentPlanId === plan.id;

  return (
    <section className="rounded-md border bg-background p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{plan.name}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{plan.description}</p>
        </div>
        {isCurrent ? <Badge>Current</Badge> : null}
      </div>
      <p className="mt-5 text-3xl font-semibold">
        ${plan.price_monthly}
        <span className="text-sm font-normal text-muted-foreground"> / month</span>
      </p>
      <Button className="mt-5 w-full" disabled={disabled || isCurrent} onClick={onCheckout}>
        <CreditCard className="size-4" aria-hidden />
        {busy ? "Opening..." : isCurrent ? "Active" : "Start checkout"}
      </Button>
    </section>
  );
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="truncate font-medium">{value}</dd>
    </div>
  );
}

function QuotaPanel({
  quota,
}: {
  quota: {
    used_turns: number;
    quota: number;
    percent: number;
    warning: boolean;
  };
}) {
  const percent = Math.min(100, Math.max(0, quota.percent));
  return (
    <section className="rounded-md border bg-background p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">Agent usage</h2>
        <span className="text-sm font-medium tabular-nums">{percent}%</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full bg-primary" style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-2 text-sm text-muted-foreground">
        {quota.used_turns} of {quota.quota} turns this month
      </p>
      {quota.warning ? (
        <p className="mt-3 rounded-md border border-amber-400/40 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950/20 dark:text-amber-100">
          You are near this month's agent quota.
        </p>
      ) : null}
    </section>
  );
}
