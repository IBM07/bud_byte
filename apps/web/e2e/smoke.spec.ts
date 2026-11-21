import { expect, test } from "@playwright/test";

test("home page renders and shows API status", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "BudByte" })).toBeVisible();

  const status = page.getByRole("main").getByTestId("api-status");
  await expect(status.getByRole("heading", { level: 2, name: "All systems go" })).toBeVisible();
  await expect(page.getByRole("main").getByTestId("check-database")).toHaveText("ok");
  await expect(page.getByRole("main").getByTestId("check-redis")).toHaveText("ok");

  expect(errors).toEqual([]);
});

// Normally a ring scales out behind the dot ("ping"). Under prefers-reduced-motion there is
// no movement, but the visible dot fades ("pulse"), so live feedback stays (docs/agents/ui.md).
for (const [reducedMotion, ring, dot] of [
  ["no-preference", "ping", "none"],
  ["reduce", "none", "pulse"],
] as const) {
  test(`status indicator with reducedMotion=${reducedMotion}: ring ${ring}, dot ${dot}`, async ({
    browser,
  }) => {
    const context = await browser.newContext({ reducedMotion });
    const page = await context.newPage();
    await page.goto("/");
    const parts = page.getByRole("main").getByTestId("api-status").locator("span[aria-hidden] > span");
    await expect(parts.nth(0)).toHaveCSS("animation-name", ring);
    await expect(parts.nth(1)).toHaveCSS("animation-name", dot);
    await context.close();
  });
}
