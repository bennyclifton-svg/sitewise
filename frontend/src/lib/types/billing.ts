export type BillingPlan = {
  id: string;
  name: string;
  description: string;
  price_monthly: number;
  configured: boolean;
};

export type BillingPlansResponse = {
  polar_enabled: boolean;
  environment: "sandbox" | "production";
  plans: BillingPlan[];
};

export type BillingStatus = {
  polar_enabled: boolean;
  environment: "sandbox" | "production";
  current_plan_id: string;
  subscription_status: string;
  read_only: boolean;
  has_polar_customer: boolean;
};
