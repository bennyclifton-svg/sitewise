import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export const taxonomyKeys = {
  root: ["taxonomy"] as const,
};

export function useTaxonomy() {
  return useQuery({
    queryKey: taxonomyKeys.root,
    queryFn: () => api.getTaxonomy(),
    staleTime: Infinity,
  });
}
