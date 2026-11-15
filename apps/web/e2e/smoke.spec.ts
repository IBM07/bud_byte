import { expect, test } from "@playwright/test";

test("home page renders and shows API status", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "BudByte" })).toBeVisible();

  const status = page.getByTestId("api-status");
  await expect(status).toBeVisible();
  await expect(status).toHaveAttribute("data-state", "ok");
  await expect(page.getByTestId("check-database")).toHaveText("ok");
  await expect(page.getByTestId("check-redis")).toHaveText("ok");

  expect(errors).toEqual([]);
});

test("respects reduced motion", async ({ browser }) => {
  const context = await browser.newContext({ reducedMotion: "reduce" });
  const page = await context.newPage();
  await page.goto("/");
  await expect(page.getByTestId("api-status")).toBeVisible();
  await context.close();
});
