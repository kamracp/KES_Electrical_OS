import { useCallback, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";

import {
  calculateCableSizing,
  type CableSizingRequest,
  type CableSizingResponse,
} from "../services/cable";

/**
 * Cable sizing mutation.
 *
 * - One in-flight request at a time: a new submit aborts the previous one.
 * - The in-flight request is aborted on unmount so no state update lands on
 *   an unmounted component.
 * - Results, errors and warnings are returned exactly as the service parsed
 *   them; nothing is reformatted here.
 */
export function useCableSizing() {
  const controllerRef = useRef<AbortController | null>(null);

  const mutation = useMutation<CableSizingResponse, Error, CableSizingRequest>({
    mutationKey: ["electrical", "cable", "calculate"],
    mutationFn: (payload) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      return calculateCableSizing(payload, controller.signal);
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
    result: mutation.data ?? null,
    error: mutation.error,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
  };
}

export type UseCableSizingResult = ReturnType<typeof useCableSizing>;
