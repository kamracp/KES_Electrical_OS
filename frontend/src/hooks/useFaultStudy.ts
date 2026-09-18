import { useCallback, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";

import {
  createFaultRun,
  type FaultRunResponse,
  type ShortCircuitStudyRequest,
} from "../services/fault";

/**
 * Short-circuit study mutation (EOS-04).
 *
 * Mirrors useCableSizing:
 * - One in-flight request at a time: a new submit aborts the previous one.
 * - The in-flight request is aborted on unmount so no state update lands on
 *   an unmounted component.
 * - Every calculation is persisted as a run (Master Prompt v2.1 item 16b);
 *   the typed result and the run summary are exposed exactly as parsed.
 */
export function useFaultStudy() {
  const controllerRef = useRef<AbortController | null>(null);

  const mutation = useMutation<FaultRunResponse, Error, ShortCircuitStudyRequest>({
    mutationKey: ["electrical", "fault", "runs", "create"],
    mutationFn: (payload) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      return createFaultRun(payload, controller.signal);
    },
  });

  useEffect(() => {
    return () => {
      controllerRef.current?.abort();
    };
  }, []);

  const calculate = useCallback(
    (payload: ShortCircuitStudyRequest) => mutation.mutateAsync(payload),
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

export type UseFaultStudyResult = ReturnType<typeof useFaultStudy>;
