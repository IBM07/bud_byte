import { getApiStatus } from "@/lib/api";

const DOT = {
  ok: "bg-emerald-500",
  degraded: "bg-amber-500",
  down: "bg-rose-500",
} as const;

export async function ApiStatusCard() {
  const status = await getApiStatus();
  const tone = status.state === "down" ? "down" : status.ready ? "ok" : "degraded";
  const label =
    tone === "ok" ? "All systems go" : tone === "degraded" ? "API up, dependencies degraded" : "API unreachable";

  return (
    <section
      aria-live="polite"
      data-testid="api-status"
      data-state={tone}
      className="w-full max-w-md rounded-2xl border border-black/10 bg-white/60 p-6 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/5"
    >
      <div className="flex items-center gap-3">
        <span className="relative flex h-3 w-3" aria-hidden="true">
          <span
            className={`absolute inline-flex h-full w-full rounded-full opacity-60 motion-safe:animate-ping ${DOT[tone]}`}
          />
          {/* Reduced motion: no expanding ring; the visible dot itself fades instead. */}
          <span
            className={`relative inline-flex h-3 w-3 rounded-full motion-reduce:animate-pulse ${DOT[tone]}`}
          />
        </span>
        <h2 className="text-lg font-medium">{label}</h2>
      </div>
      {status.state === "up" ? (
        <dl className="mt-4 grid grid-cols-2 gap-y-2 text-sm text-black/70 dark:text-white/70">
          <dt>API version</dt>
          <dd className="text-right font-mono">{status.health.version}</dd>
          {Object.entries(status.readiness.checks).map(([name, result]) => (
            <div key={name} className="contents">
              <dt className="capitalize">{name}</dt>
              <dd className="text-right font-mono" data-testid={`check-${name}`}>
                {result}
              </dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="mt-4 text-sm text-black/70 dark:text-white/70">
          Could not reach the API ({status.reason}).
        </p>
      )}
    </section>
  );
}

export function ApiStatusSkeleton() {
  return (
    <div
      data-testid="api-status-loading"
      className="h-[148px] w-full max-w-md rounded-2xl border border-black/10 bg-black/[0.03] motion-safe:animate-pulse dark:border-white/10 dark:bg-white/5"
    />
  );
}
