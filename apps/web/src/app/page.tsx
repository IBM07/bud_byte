import { Suspense } from "react";

import { ApiStatusCard, ApiStatusSkeleton } from "./api-status";

// Phase 1 placeholder. The real landing page and design system arrive in Phase 5.
export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-8 px-4 py-16">
      <header className="text-center">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">BudByte</h1>
        <p className="mt-3 text-base text-black/60 dark:text-white/60">
          Your buddy that remembers, nudges and does. Coming soon.
        </p>
      </header>
      <Suspense fallback={<ApiStatusSkeleton />}>
        <ApiStatusCard />
      </Suspense>
    </main>
  );
}
