function required(value: string | undefined, name: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value.trim();
}

export const env = {
  apiBaseUrl: required(
    import.meta.env.VITE_API_BASE_URL,
    "VITE_API_BASE_URL",
  ),
  supabaseUrl: required(import.meta.env.VITE_SUPABASE_URL, "VITE_SUPABASE_URL"),
  supabaseAnonKey: required(
    import.meta.env.VITE_SUPABASE_ANON_KEY,
    "VITE_SUPABASE_ANON_KEY",
  ),
} as const;
