import { useCallback, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";

import { useProject } from "../app/projectContext";

import {
  createLoadRun,
  type LoadRunCreateRequest,
  type LoadRunResponse,
} from "../services/loadDemand";

/**
 * Load and demand study mutation (EOS-02).
 *
 * Mirrors useFaultStudy:
 * - One in-flight request at a time: a new submit aborts the previous one.
 * - The in-flight request is aborted on unmount so no state update lands on
 *   an unmounted component.
 * - The run is attached to the revision chosen in the top bar, read at submit time; with
 *   no project, or one without an open revision, nothing is sent and the run is unassigned.
 * - Every calculation is persisted as a run (Master Prompt A15 (d)); the typed
 *   result and the run summary are exposed exactly as parsed.
 *
 * The request is the whole run body, so the study's notes travel with it; the
 * form never puts a project revision in it.
 */
export function useLoadStudy() {
  const controllerRef = useRef<AbortController | null>(null);
  const { activeRevisionId } = useProject();

  const mutation = useMutation<LoadRunResponse, Error, LoadRunCreateRequest>({
    mutationKey: ["electrical", "load-demand", "runs", "create"],
    mutationFn: (payload) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      return createLoadRun(payload, controller.signal, activeRevisionId() ?? undefined);
    },
  });

  useEffect(() => {
    return () => {
      controllerRef.current?.abort();
    };
  }, []);

  const calculate = useCallback(
    (payload: LoadRunCreateRequest) => mutation.mutateAsync(payload),
    [mutation],
  );

  const reset = useCallback(() => {
    controllerRef.current?.abort();
    mutation.reset();
  }, [mutation]);

  return {
    calculate,
    reset,
    result: mutation.data?.result ?? null,
    run: mutation.data?.run ?? null,
    error: mutation.error,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
  };
}

export type UseLoadStudyResult = ReturnType<typeof useLoadStudy>;
