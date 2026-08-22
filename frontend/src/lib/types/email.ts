export type ProjectEmailDraft = {
  id: string;
  project_id: string;
  status: string;
  to_addresses: string[];
  cc_addresses: string[];
  subject: string;
  body_text: string;
  in_reply_to_email_id: string | null;
  provider_draft_id: string | null;
  provider_message_id: string | null;
  send_error: string | null;
  sent_at: string | null;
  sent_by_user_id: string | null;
};

export type ProjectEmailMessage = {
  email_id: string;
  project_id?: string | null;
  subject: string;
  body_text: string;
  from_address: string;
  to_addresses?: string[];
  cc_addresses?: string[];
  sent_at: string | null;
  message_category?: string | null;
};

export type ProjectEmailRegisterRow = {
  id: string;
  kind: "inbound" | "outbound";
  direction: "in" | "out";
  subject: string;
  party: string;
  sent_at: string | null;
  message_category: string | null;
  status: string | null;
  email_id: string | null;
  draft_id: string | null;
};
