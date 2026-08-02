export type BillingPlan = {
  id: string;
  name: string;
  description: string;
  price_monthly: number;
  configured: boolean;
};

export type BillingPlansResponse = {
  billing_provider: "none" | "stripe" | string;
  billing_enabled: boolean;
  environment: string;
  plans: BillingPlan[];
};

export type AgentQuota = {
  used_turns: number;
  quota: number;
  percent: number;
  warning: boolean;
};

export type BillingStatus = {
  billing_provider: "none" | "stripe" | string;
  billing_enabled: boolean;
  environment: string;
  current_plan_id: string;
  subscription_status: string;
  read_only: boolean;
  has_customer: boolean;
  quota: AgentQuota;
};
