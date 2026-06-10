import { QueryClient } from "@tanstack/react-query";

/**
 * Shared QueryClient for the app.
 *
 * Defaults are tuned for a latency-bound SPA talking to a remote Supabase
 * backend: keep data fresh for a short window so navigating between screens
 * renders instantly from cache, and avoid surprise refetches on window focus.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});
