import { useId } from "react";
import { useQuery } from "@tanstack/react-query";

import { getHealth } from "../services/health";

export function ApiHealthStatus() {
  const headingId = useId();
  const health = useQuery({
    queryKey: ["system", "health"],
    queryFn: ({ signal }) => getHealth(signal),
    refetchOnMount: "always",
  });

  let message = "Connection has not been checked.";

  if (health.isPaused) {
    message = "Waiting for a network connection.";
  } else if (health.isFetching || health.isPending) {
    message = "Checking service connection...";
  } else if (health.isError) {
    message = "Connection check failed. Try again.";
  } else if (health.isSuccess) {
    message = "Last check: connected.";
  }

  return (
    <section aria-labelledby={headingId} aria-busy={health.isFetching}>
      <h2 id={headingId}>Service connection</h2>
      <p role="status">{message}</p>
      <button
        type="button"
        disabled={health.isFetching || health.isPaused}
        onClick={() => {
          void health.refetch();
        }}
      >
        {health.isFetching ? "Checking..." : "Check connection"}
      </button>
    </section>
  );
}
