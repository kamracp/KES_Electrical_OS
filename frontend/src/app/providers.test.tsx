// @vitest-environment jsdom

import { StrictMode, type PropsWithChildren } from "react";
import { cleanup, renderHook } from "@testing-library/react";
import { useQueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, it } from "vitest";

import { AppProviders } from "./providers";

function TestProviders({ children }: PropsWithChildren) {
  return (
    <StrictMode>
      <AppProviders>{children}</AppProviders>
    </StrictMode>
  );
}

afterEach(() => {
  cleanup();
});

describe("AppProviders", () => {
  it("preserves the query client and cached data across rerenders", () => {
    const { result, rerender } = renderHook(() => useQueryClient(), {
      wrapper: TestProviders,
    });
    const client = result.current;

    try {
      client.setQueryData(["provider-test"], { value: "cached" });
      rerender();

      expect(result.current).toBe(client);
      expect(result.current.getQueryData(["provider-test"])).toEqual({
        value: "cached",
      });
    } finally {
      client.clear();
    }
  });

  it("keeps separate provider trees from sharing cached data", () => {
    const first = renderHook(() => useQueryClient(), {
      wrapper: TestProviders,
    });
    const second = renderHook(() => useQueryClient(), {
      wrapper: TestProviders,
    });

    try {
      first.result.current.setQueryData(["provider-test"], "first tree");

      expect(second.result.current).not.toBe(first.result.current);
      expect(second.result.current.getQueryData(["provider-test"])).toBeUndefined();
      expect(first.result.current.getQueryData(["provider-test"])).toBe("first tree");
    } finally {
      first.result.current.clear();
      second.result.current.clear();
    }
  });
});
