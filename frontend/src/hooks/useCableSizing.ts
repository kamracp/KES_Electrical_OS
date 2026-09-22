import { useCallback, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";

import { useProject } from "../app/projectContext";

import {
  createCableRun,
  type CableRunResponse,
  type CableSizingRequest,
} from "../services/cable";

/**
 * Cable sizing mutation.
 *
 * - One in-flight request at a time: a new submit aborts the previous one.
 * - The in-flight request is aborted on unmount so no state update lands on
 *   an unmounted component.
 * - The run is attached to the revision chosen in the top bar, read at submit time; with
 *   no project, or one without an open revision, nothing is sent and the run is unassigned.
 * - Every calculation is persisted as a run (Master Prompt v2.1 item 15);
 *   the typed result and the run summary are exposed exactly as parsed.
 */
export function useCableSizing() {
  const controllerRef = useRef<AbortController | null>(null);
  const { activeRevisionId } = useProject();

  const mutation = useMutation<CableRunResponse, Error, CableSizingRequest>({
    mutationKey: ["electrical", "cable", "runs", "create"],
    mutationFn: (payload) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      return createCableRun(payload, controller.signal, activeRevisionId() ?? undefined);
    },
  });

  useEffect(() => {
    return () => {
      controllerRef.current?.abort();
    };
  }, []);

  const calculate = useCallback(
    (payload: CableSizingRequest) => mutation.mutateAsync(payload),
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

export type UseCableSizingResult = ReturnType<typeof useCableSizing>;
