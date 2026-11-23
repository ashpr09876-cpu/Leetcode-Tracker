import { expect, test } from "@playwright/test";

// Needs the full stack running (backend + database + frontend). See docs/DEVELOPMENT.md.
test("main user journey: register, add/edit problem, note, revision, analytics, logout, login, data persists", async ({ page }) => {
  const email = `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
  const password = "E2e-password-123";

  await page.goto("/register");
  await page.getByLabel("Name").fill("E2E User");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  await page.goto("/problems");
  await page.getByRole("button", { name: /Add problem/ }).first().click();
  const dialog = page.getByRole("dialog", { name: "Add problem" });
  await dialog.getByLabel("Title").fill("Two Sum");
  await dialog.getByLabel("Difficulty").selectOption("easy");
  await dialog.getByLabel("Status").selectOption("solved");
  await dialog.getByRole("button", { name: "Add problem" }).click();
  await expect(page.getByRole("link", { name: "Two Sum" })).toBeVisible();

  await page.getByRole("link", { name: "Two Sum" }).click();
  await page.getByRole("button", { name: "Edit" }).click();
  const edit = page.getByRole("dialog", { name: "Edit problem" });
  await edit.getByLabel("Title").fill("Two Sum (revised)");
  await edit.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("heading", { name: "Two Sum (revised)" })).toBeVisible();

  await page.getByLabel("New note").fill("Use a hash map for O(n).");
  await page.getByRole("button", { name: "Add note" }).click();
  await expect(page.getByText("Use a hash map for O(n).")).toBeVisible();

  await page.getByRole("button", { name: "Schedule revision" }).click();
  await page.goto("/revisions");
  await expect(page.getByText("Two Sum (revised)")).toBeVisible();

  await page.goto("/analytics");
  await expect(page.getByRole("heading", { name: "Difficulty distribution" })).toBeVisible();

  await page.goto("/");
  await page.evaluate(() => (document.querySelector("[aria-label='Open menu']") as HTMLElement | null)?.click());
  await page.getByRole("button", { name: "Log out" }).first().click();
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.goto("/problems");
  await expect(page.getByRole("link", { name: "Two Sum (revised)" })).toBeVisible();
});
