import { test, expect } from "@playwright/test";

for (const width of [390, 1280]) {
  test("application workspace at " + width + "px", async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(
      page.getByRole("button", { name: "Explore loan options" }),
    ).toBeEnabled();
    await page.evaluate(() => document.fonts.ready);
    await expect(
      page.getByRole("heading", { name: "Application progress" }),
    ).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await page.screenshot({
      path: info.outputPath("workspace.png"),
      fullPage: true,
    });
    await page.getByRole("button", { name: "Explore loan options" }).click();
    await expect(page.locator(".message.bot").last()).toContainText("PAN");
  });
}
