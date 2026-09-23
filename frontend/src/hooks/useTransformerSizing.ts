import { useCallback, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";

import { useProject } from "../app/projectContext";

import {
  createTransformerRun,
  type TransformerRunCreateRequest,
  type TransformerRunResponse,
} from "../services/transformerSizing";

/**
 * Transformer sizing study mutation (EOS-03a).
 *
 * Mirrors useLoadStudy:
 * - One in-flight request at a time: a new submit aborts the previous one.
 * - The in-flight request is aborted on unmount so no state update lands on
 *   an unmounted component.
 * - The run is attached to the revision chosen in the top bar, read at submit time; with
 *   no project, or one without an open revision, nothing is sent and the run is unassigned.
 * - Every calculation is persisted as a run (Master Prompt A16); the typed
 *   result and the run summary are exposed exactly as parsed, including a
 *   NO_SOLUTION result - "no rating fits" is engineering evidence too.
 *
 * The request is the whole run body, so the study's notes travel with it; the
 * form never puts a project revision in it.
 */
export function useTransformerSizing() {
  const controllerRef = useRef<AbortController | null>(null);
  const { activeRevisionId } = useProject();

  const mutation = useMutation<TransformerRunResponse, Error, TransformerRunCreateRequest>({
    mutationKey: ["electrical", "transformer-sizing", "runs", "create"],
    mutationFn: (payload) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      return createTransformerRun(payload, controller.signal, activeRevisionId() ?? undefined);
    },
  });

  useEffect(() => {
    return () => {
      controllerRef.current?.abort();
    };
  }, []);

  const calculate = useCallback(
    (payload: TransformerRunCreateRequest) => mutation.mutateAsync(payload),
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

export type UseTransformerSizingResult = ReturnType<typeof useTransformerSizing>;
