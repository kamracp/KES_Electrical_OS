// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider, onlineManager } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getHealth, type HealthResponse } from "../services/health";
import { ApiHealthStatus } from "./ApiHealthStatus";

vi.mock("../services/health", () => ({ getHealth: vi.fn() }));

const getHealthMock = vi.mocked(getHealth);
const healthyResponse: HealthResponse = {
  status: "healthy",
  application: "KES Electrical OS API",
};

let client: QueryClient;
let previousOnlineState: boolean;

function deferredHealth() {
  let resolve!: (value: HealthResponse) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<HealthResponse>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function renderStatus() {
  return render(
    <QueryClientProvider client={client}>
      <ApiHealthStatus />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  previousOnlineState = onlineManager.isOnline();
  onlineManager.setOnline(true);
  getHealthMock.mockReset();
  client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity, refetchOnWindowFocus: false },
    },
  });
});

afterEach(() => {
  cleanup();
  client.clear();
  onlineManager.setOnline(previousOnlineState);
});

describe("ApiHealthStatus", () => {
  it("shows loading, prevents duplicate checks, then announces success", async () => {
    const request = deferredHealth();
    getHealthMock.mockReturnValue(request.promise);
    renderStatus();

    expect(screen.getByRole("status")).toHaveTextContent("Checking service connection...");
    expect(screen.getByRole("region", { name: "Service connection" })).toHaveAttribute(
      "aria-busy", "true",
    );
    const button = screen.getByRole("button", { name: "Checking..." });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(getHealthMock).toHaveBeenCalledTimes(1);

    await act(async () => request.resolve(healthyResponse));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Last check: connected.");
    });
    expect(screen.getByRole("button", { name: "Check connection" })).toBeEnabled();
    expect(screen.getByRole("region", { name: "Service connection" })).toHaveAttribute(
      "aria-busy", "false",
    );
  });

  it("shows an initial failure and recovers after a manual check", async () => {
    getHealthMock
      .mockRejectedValueOnce(new Error("Service unavailable"))
      .mockResolvedValueOnce(healthyResponse);
    renderStatus();

    await screen.findByText("Connection check failed. Try again.");
    expect(getHealthMock).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Check connection" }));

    await screen.findByText("Last check: connected.");
    expect(getHealthMock).toHaveBeenCalledTimes(2);
  });

  it("hides an earlier success while rechecking and after a failed recheck", async () => {
    const recheck = deferredHealth();
    getHealthMock
      .mockResolvedValueOnce(healthyResponse)
      .mockReturnValueOnce(recheck.promise);
    renderStatus();
    await screen.findByText("Last check: connected.");

    fireEvent.click(screen.getByRole("button", { name: "Check connection" }));
    await screen.findByText("Checking service connection...");
    expect(screen.queryByText("Last check: connected.")).not.toBeInTheDocument();

    await act(async () => recheck.reject(new Error("Connection lost")));

    await screen.findByText("Connection check failed. Try again.");
    expect(screen.queryByText("Last check: connected.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Check connection" })).toBeEnabled();
    expect(getHealthMock).toHaveBeenCalledTimes(2);
  });

  it("waits while offline and checks when the network returns", async () => {
    onlineManager.setOnline(false);
    getHealthMock.mockResolvedValue(healthyResponse);
    renderStatus();

    expect(screen.getByRole("status")).toHaveTextContent("Waiting for a network connection.");
    expect(screen.getByRole("button", { name: "Check connection" })).toBeDisabled();
    expect(getHealthMock).not.toHaveBeenCalled();

    await act(async () => onlineManager.setOnline(true));

    await screen.findByText("Last check: connected.");
    expect(getHealthMock).toHaveBeenCalledTimes(1);
  });

  it("cancels the pending health request when the component unmounts", async () => {
    let requestSignal: AbortSignal | undefined;
    getHealthMock.mockImplementation((signal) => {
      if (!signal) throw new Error("A cancellation signal is required.");
      requestSignal = signal;
      return new Promise<HealthResponse>((_resolve, reject) => {
        if (signal.aborted) {
          reject(signal.reason);
        } else {
          signal.addEventListener("abort", () => reject(signal.reason), { once: true });
        }
      });
    });
    const { unmount } = renderStatus();
    expect(requestSignal?.aborted).toBe(false);

    unmount();

    await waitFor(() => expect(requestSignal?.aborted).toBe(true));
    expect(getHealthMock).toHaveBeenCalledTimes(1);
  });
});
