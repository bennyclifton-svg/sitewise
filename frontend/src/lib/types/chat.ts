export type ChatThread = {
  id: string;
  project_id: string | null;
  title: string | null;
  hermes_session_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  role: string;
  content: string;
  message_data: Record<string, unknown> | null;
  created_at: string;
};
