/**
 * Playwright E2E：DDL 完整用户流程
 * 覆盖：粘贴 DDL → 解析 → 查看 ER 图 → 配置行数 → 生成 → SQL Explorer 查询 → 导出
 *
 * 前置条件：
 *   - DataForge 运行在 http://localhost:8000
 *   - `npx playwright test` 或 `pnpm test:e2e`
 */

import { test, expect, Page } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const BASE_URL = process.env.DATAFORGE_URL ?? "http://localhost:8000";
const FIXTURES = path.join(__dirname, "../fixtures/ddl");

const ECOMMERCE_DDL = fs.readFileSync(
  path.join(FIXTURES, "ecommerce_schema.sql"),
  "utf-8"
);

test.describe("DDL 完整生成流程", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.getByTestId("schema-editor")).toBeVisible();
  });

  test("页面初始状态渲染正确", async ({ page }) => {
    await expect(page.getByTestId("schema-editor")).toBeVisible();
    await expect(page.getByTestId("btn-parse")).toBeDisabled();
    await expect(page.getByTestId("tab-er-diagram")).toBeVisible();
  });

  test("粘贴 DDL 后解析按钮变为可用", async ({ page }) => {
    await fillEditor(page, ECOMMERCE_DDL);
    await expect(page.getByTestId("btn-parse")).toBeEnabled();
  });

  test("解析 DDL 后 ER 图包含所有表节点", async ({ page }) => {
    await fillEditor(page, ECOMMERCE_DDL);
    await page.getByTestId("btn-parse").click();
    await page.waitForSelector("[data-testid='er-diagram-canvas']", { timeout: 10_000 });

    for (const table of ["categories", "products", "users", "orders", "order_items"]) {
      await expect(page.getByTestId(`er-node-${table}`)).toBeVisible();
    }
  });

  test("ER 图显示外键连线", async ({ page }) => {
    await fillEditor(page, ECOMMERCE_DDL);
    await page.getByTestId("btn-parse").click();
    await page.waitForSelector("[data-testid='er-diagram-canvas']", { timeout: 10_000 });

    // 至少有外键连线存在
    const edges = await page.locator("[data-testid^='er-edge-']").count();
    expect(edges).toBeGreaterThanOrEqual(3);
  });

  test("配置行数后生成数据", async ({ page }) => {
    await fillEditor(page, ECOMMERCE_DDL);
    await page.getByTestId("btn-parse").click();
    await page.waitForSelector("[data-testid='er-diagram-canvas']", { timeout: 10_000 });

    await page.getByTestId("tab-config").click();
    await setRowCount(page, "users", "20");
    await setRowCount(page, "orders", "50");

    await page.getByTestId("btn-generate").click();
    await expect(page.getByTestId("generate-progress")).toBeVisible();
    await page.waitForSelector("[data-testid='generate-success']", { timeout: 60_000 });
  });

  test("生成后数据预览表格显示内容", async ({ page }) => {
    await fullGenerate(page, { users: "10", categories: "5", products: "15", orders: "20", order_items: "40" });

    await page.getByTestId("tab-data-preview").click();
    await page.getByTestId("table-select-users").click();

    const rows = await page.locator("[data-testid='preview-row']").count();
    expect(rows).toBeGreaterThanOrEqual(1);
  });

  test("SQL Explorer 可查询生成的数据", async ({ page }) => {
    await fullGenerate(page, { users: "10", categories: "5", products: "15", orders: "20", order_items: "40" });

    await page.getByTestId("tab-sql-explorer").click();
    await fillMonaco(page, "[data-testid='sql-editor']", "SELECT COUNT(*) AS cnt FROM users");
    await page.getByTestId("btn-run-sql").click();

    await expect(page.getByTestId("sql-result-table")).toBeVisible({ timeout: 10_000 });
    const firstCell = page.locator("[data-testid='sql-result-row']:first-child td").first();
    await expect(firstCell).toHaveText("10");
  });

  test("JOIN 查询在 SQL Explorer 中执行成功", async ({ page }) => {
    await fullGenerate(page, { users: "5", categories: "3", products: "10", orders: "8", order_items: "20" });

    await page.getByTestId("tab-sql-explorer").click();
    await fillMonaco(page, "[data-testid='sql-editor']", `
      SELECT u.username, COUNT(o.id) AS order_count
      FROM users u
      LEFT JOIN orders o ON o.user_id = u.id
      GROUP BY u.username
    `);
    await page.getByTestId("btn-run-sql").click();

    await expect(page.getByTestId("sql-result-table")).toBeVisible({ timeout: 10_000 });
    const rowCount = await page.locator("[data-testid='sql-result-row']").count();
    expect(rowCount).toBe(5);
  });

  test("导出 SQL 文件可下载", async ({ page }) => {
    await fullGenerate(page, { users: "5", categories: "3", products: "10", orders: "8", order_items: "15" });

    await page.getByTestId("tab-export").click();
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByTestId("btn-export-sql").click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.sql$/);
  });

  test("导出 CSV ZIP 文件可下载", async ({ page }) => {
    await fullGenerate(page, { users: "5", categories: "3", products: "10", orders: "8", order_items: "15" });

    await page.getByTestId("tab-export").click();
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByTestId("btn-export-csv").click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.zip$/);
  });
});

// ── 辅助函数 ─────────────────────────────────────────────────────────────────

async function fillEditor(page: Page, content: string) {
  const editor = page.getByTestId("schema-editor");
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.type(content);
}

async function fillMonaco(page: Page, selector: string, content: string) {
  const el = page.locator(selector);
  await el.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.type(content);
}

async function setRowCount(page: Page, table: string, count: string) {
  const input = page.getByTestId(`row-count-${table}`);
  await input.fill(count);
}

async function fullGenerate(page: Page, rowCounts: Record<string, string>) {
  await fillEditor(page, ECOMMERCE_DDL);
  await page.getByTestId("btn-parse").click();
  await page.waitForSelector("[data-testid='er-diagram-canvas']", { timeout: 10_000 });

  await page.getByTestId("tab-config").click();
  for (const [table, count] of Object.entries(rowCounts)) {
    await setRowCount(page, table, count);
  }

  await page.getByTestId("btn-generate").click();
  await page.waitForSelector("[data-testid='generate-success']", { timeout: 60_000 });
}
