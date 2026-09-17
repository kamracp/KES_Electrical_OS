import { useCallback, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";

import {
  calculateFaultStudy,
  type ShortCircuitStudyRequest,
  type ShortCircuitStudyResponse,
} from "../services/fault";

/**
 * Short-circuit study mutation (EOS-04).
 *
 * Mirrors useCableSizing:
 * - One in-flight request at a time: a new submit aborts the previous one.
 * - The in-flight request is aborted on unmount so no state update lands on
 *   an unmounted component.
 * - Results, errors and warnings are returned exactly as the service parsed
 *   them; nothing is reformatted here.
 */
export function useFaultStudy() {
  const controllerRef = useRef<AbortController | null>(null);

  const mutation = useMutation<
    ShortCircuitStudyResponse,
    Error,
    ShortCircuitStudyRequest
  >({
    mutationKey: ["electrical", "fault", "calculate"],
    mutationFn: (payload) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      return calculateFaultStudy(payload, controller.signal);
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
    result: mutation.data ?? null,
    error: mutation.error,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
  };
}

export type UseFaultStudyResult = ReturnType<typeof useFaultStudy>;
