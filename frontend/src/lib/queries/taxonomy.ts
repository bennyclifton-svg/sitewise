import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export const taxonomyKeys = {
  // Bump when taxonomy JSON shape/labels change so pinned client caches refetch.
  root: ["taxonomy", "v2"] as const,
};

export function useTaxonomy() {
  return useQuery({
    queryKey: taxonomyKeys.root,
    queryFn: () => api.getTaxonomy(),
    // Taxonomy JSON can change without a frontend rebuild; do not pin forever.
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  });
}
