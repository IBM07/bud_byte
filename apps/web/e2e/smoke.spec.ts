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

// The status pulse scales out ("ping") normally; under prefers-reduced-motion the movement
// is replaced by an opacity fade ("pulse"), so the live feedback stays (docs/agents/ui.md).
for (const [reducedMotion, animation] of [
  ["no-preference", "ping"],
  ["reduce", "pulse"],
] as const) {
  test(`status pulse animation is "${animation}" with reducedMotion=${reducedMotion}`, async ({
    browser,
  }) => {
    const context = await browser.newContext({ reducedMotion });
    const page = await context.newPage();
    await page.goto("/");
    const pulse = page
      .getByRole("main")
      .getByTestId("api-status")
      .locator("span[aria-hidden] > span")
      .first();
    await expect(pulse).toHaveCSS("animation-name", animation);
    await context.close();
  });
}
