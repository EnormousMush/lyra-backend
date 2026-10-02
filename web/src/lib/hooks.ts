import { useQuery } from "@tanstack/react-query";
import { api, ApiError, type TrackDetail } from "./api";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api.me();
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    staleTime: 60_000,
  });
}

export function useMeta() {
  return useQuery({ queryKey: ["meta"], queryFn: api.meta, staleTime: 300_000 });
}

export function useTracks() {
  return useQuery({
    queryKey: ["tracks"],
    queryFn: api.tracks,
    refetchInterval: (q) => (q.state.data?.some((t) => t.stage !== "ready" && t.stage !== "error") ? 2000 : false),
  });
}

const pending = (t?: TrackDetail) =>
  !!t &&
  ((t.stage !== "ready" && t.stage !== "error") ||
    t.generations.some((g) => g.status === "planning" || g.status === "rendering"));

export function useTrack(id: string) {
  return useQuery({
    queryKey: ["track", id],
    queryFn: () => api.track(id),
    refetchInterval: (q) => (pending(q.state.data) ? 1500 : false),
  });
}
