import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export const agentConfigurationKey = ["agent-configuration"] as const;

export function useAgentConfiguration() {
  return useQuery({
    queryKey: agentConfigurationKey,
    queryFn: api.getAgentConfiguration,
    staleTime: 5 * 60_000,
  });
}
