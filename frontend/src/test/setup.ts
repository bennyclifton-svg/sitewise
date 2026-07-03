import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});

const testEnv = import.meta.env as unknown as Record<string, string | undefined>;

testEnv.VITE_API_BASE_URL ??= "http://localhost:8000";
testEnv.VITE_SUPABASE_URL ??= "http://localhost:54321";
testEnv.VITE_SUPABASE_ANON_KEY ??= "test-anon-key";
