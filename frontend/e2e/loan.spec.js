import process from "node:process";
import { test, expect } from "@playwright/test";
import { readFile, writeFile } from "node:fs/promises";

async function say(page, message, reply) {
  const input = page.getByPlaceholder("Type your message...");
  await input.fill(message);
  await input.press("Enter");
  await expect(page.locator(".message.bot").last()).toContainText(reply);
  if (process.env.RECORD_DEMO) await page.waitForTimeout(1500);
}

async function apply(page, {pan, amount, phone, address, expected}) {
  await page.goto("/?campaign=education");
  await say(page, "Hello", "education");
  await say(page, "I need " + amount + " for course fees", "PAN");
  await say(page, pan, "income");
  await say(page, "60000", "36 months");
  await say(page, "24 months", "Application Summary");
  await say(page, "yes", "phone");
  await say(page, phone, "street address");
  await say(page, address, expected);
}

test("salary slip approval survives refresh and produces a PDF", async ({page}) => {
  await apply(page, {pan: "ABCDE1234F", amount: "300000", phone: "0000000001",
    address: "11 Demo Lane", expected: "salary slip"});
  await page.reload();
  const sample = page.getByRole("link", {name: "Download demo salary slip"});
  const downloaded = page.waitForEvent("download");
  await sample.click();
  const file = await downloaded;
  await page.locator('input[type="file"]').setInputFiles({
    name: file.suggestedFilename(), mimeType: "application/pdf", buffer: await readFile(await file.path())
  });
  const link = page.getByRole("link", {name: "Download Letter"});
  await expect(link).toBeVisible();
  const letter = await page.request.get(await link.getAttribute("href"));
  expect(letter.headers()["content-type"]).toBe("application/pdf");
  expect((await letter.body()).subarray(0, 5).toString()).toBe("%PDF-");
  if (process.env.RECORD_DEMO) {
    await writeFile(test.info().outputPath("sanction.pdf"), await letter.body());
    await page.waitForTimeout(2500);
  }
  await page.reload();
  await expect(link).toBeVisible();
});

test("instant approval", async ({page}) => {
  await apply(page, {pan: "ABCDE1234F", amount: "100000", phone: "0000000001",
    address: "11 Demo Lane", expected: "approved"});
  await expect(page.getByRole("link", {name: "Download Letter"})).toBeVisible();
});

test("custom profile creates its own offer and sanction letter", async ({page}) => {
  await page.goto("/");
  await page.getByRole("button", {name: "Use my own profile"}).click();
  for (const [label, value] of [
    ["Applicant name", "Sample Applicant"], ["Demo phone", "0000000012"],
    ["Demo street address", "12 Sample Road"], ["Monthly take-home salary", "65000"],
    ["Simulated credit score", "715"], ["Simulated pre-approved limit", "110000"],
  ]) {
    await page.getByLabel(label).fill(value);
  }
  await page.getByRole("button", {name: "Start custom application"}).click();
  await expect(page.locator(".message.bot").last()).toContainText("How much");
  await say(page, "105000", "36 months");
  await say(page, "24 months", "Application Summary");
  await say(page, "yes", "phone");
  await say(page, "0000000012", "street address");
  await say(page, "12 Sample Road", "approved");
  await page.reload();
  await expect(page.getByRole("link", {name: "Download Letter"})).toBeVisible();
});

test("low score rejection", async ({page}) => {
  await apply(page, {pan: "LOWSC0000X", amount: "100000", phone: "0000000003",
    address: "7 Model Street", expected: "below 700"});
  await expect(page.getByRole("link", {name: "Download Letter"})).toHaveCount(0);
});
