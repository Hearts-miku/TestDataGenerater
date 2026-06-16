/**
 * Playwright E2E：Cypher 完整用户流程
 * 覆盖：粘贴 Cypher → 解析 → 图谱预览 → 生成 → Cypher Explorer 查询
 */

import { test, expect, Page } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const BASE_URL = process.env.DATAFORGE_URL ?? "http://localhost:8000";
const CYPHER_SOCIAL = fs.readFileSync(
  path.join(__dirname, "../fixtures/cypher/social_network.cypher"),
  "utf-8"
);

test.describe("Cypher 完整生成流程", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.getByTestId("schema-type-toggle").getByText("Cypher").click();
    await expect(page.getByTestId("schema-editor")).toBeVisible();
  });

  test("切换到 Cypher 模式后编辑器语言变为 cypher", async ({ page }) => {
    const editorLang = await page.getByTestId("schema-editor").getAttribute("data-language");
    expect(editorLang).toBe("cypher");
  });

  test("解析后图谱视图显示节点标签", async ({ page }) => {
    await fillEditor(page, CYPHER_SOCIAL);
    await page.getByTestId("btn-parse").click();
    await page.waitForSelector("[data-testid='graph-view-canvas']", { timeout: 10_000 });

    for (const label of ["User", "Post", "Tag"]) {
      await expect(page.getByTestId(`graph-label-${label}`)).toBeVisible();
    }
  });

  test("图谱视图显示关系类型徽标", async ({ page }) => {
    await fillEditor(page, CYPHER_SOCIAL);
    await page.getByTestId("btn-parse").click();
    await page.waitForSelector("[data-testid='graph-view-canvas']", { timeout: 10_000 });

    const relBadges = await page.locator("[data-testid^='graph-rel-']").count();
    expect(relBadges).toBeGreaterThanOrEqual(4);
  });

  test("生成节点和关系后统计正确", async ({ page }) => {
    await fillEditor(page, CYPHER_SOCIAL);
    await page.getByTestId("btn-parse").click();
    await page.waitForSelector("[data-testid='graph-view-canvas']", { timeout: 10_000 });

    await page.getByTestId("tab-config").click();
    await setNodeCount(page, "User", "20");
    await setNodeCount(page, "Post", "40");
    await setNodeCount(page, "Tag", "10");
    await setRelCount(page, "FOLLOWS", "30");
    await setRelCount(page, "AUTHORED", "40");

    await page.getByTestId("btn-generate").click();
    await page.waitForSelector("[data-testid='generate-success']", { timeout: 60_000 });

    const statsText = await page.getByTestId("generate-stats").innerText();
    expect(statsText).toContain("20");
  });

  test("Cypher Explorer 可执行 MATCH 查询", async ({ page }) => {
    await generateSocial(page, { User: "15", Post: "30", Tag: "8", FOLLOWS: "20", AUTHORED: "30" });

    await page.getByTestId("tab-cypher-explorer").click();
    await fillMonaco(page, "[data-testid='cypher-editor']",
      "MATCH (u:User) RETURN count(u) AS cnt"
    );
    await page.getByTestId("btn-run-cypher").click();

    await expect(page.getByTestId("cypher-result-table")).toBeVisible({ timeout: 10_000 });
    const firstCell = page.locator("[data-testid='cypher-result-row']:first-child td").first();
    await expect(firstCell).toHaveText("15");
  });

  test("Cypher Explorer 查询结果可渲染为局部图", async ({ page }) => {
    await generateSocial(page, { User: "10", Post: "20", Tag: "5", FOLLOWS: "15", AUTHORED: "20" });

    await page.getByTestId("tab-cypher-explorer").click();
    await fillMonaco(page, "[data-testid='cypher-editor']",
      "MATCH (u:User)-[:AUTHORED]->(p:Post) RETURN u, p LIMIT 5"
    );
    await page.getByTestId("btn-run-cypher").click();

    await page.getByTestId("btn-view-as-graph").click();
    await expect(page.getByTestId("cypher-result-graph")).toBeVisible({ timeout: 10_000 });
    const nodeCount = await page.locator("[data-testid^='result-node-']").count();
    expect(nodeCount).toBeGreaterThan(0);
  });

  test("写操作在 Cypher Explorer 中被拒绝", async ({ page }) => {
    await generateSocial(page, { User: "5" });

    await page.getByTestId("tab-cypher-explorer").click();
    await fillMonaco(page, "[data-testid='cypher-editor']",
      "MATCH (n) DETACH DELETE n"
    );
    await page.getByTestId("btn-run-cypher").click();

    await expect(page.getByTestId("cypher-error-banner")).toBeVisible({ timeout: 5_000 });
    const errorText = await page.getByTestId("cypher-error-banner").innerText();
    expect(errorText.toLowerCase()).toMatch(/forbidden|not allowed|只读/i);
  });

  test("导出 Cypher CREATE 语句", async ({ page }) => {
    await generateSocial(page, { User: "5", Post: "10", Tag: "3", FOLLOWS: "8", AUTHORED: "10" });

    await page.getByTestId("tab-export").click();
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByTestId("btn-export-cypher").click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.cypher$|\.cql$/);
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
  await page.locator(selector).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.type(content);
}

async function setNodeCount(page: Page, label: string, count: string) {
  await page.getByTestId(`node-count-${label}`).fill(count);
}

async function setRelCount(page: Page, type: string, count: string) {
  await page.getByTestId(`rel-count-${type}`).fill(count);
}

async function generateSocial(page: Page, counts: Record<string, string>) {
  await fillEditor(page, CYPHER_SOCIAL);
  await page.getByTestId("btn-parse").click();
  await page.waitForSelector("[data-testid='graph-view-canvas']", { timeout: 10_000 });

  await page.getByTestId("tab-config").click();
  for (const [key, count] of Object.entries(counts)) {
    const nodeInput = page.getByTestId(`node-count-${key}`);
    const relInput  = page.getByTestId(`rel-count-${key}`);
    if (await nodeInput.count()) await nodeInput.fill(count);
    if (await relInput.count()) await relInput.fill(count);
  }

  await page.getByTestId("btn-generate").click();
  await page.waitForSelector("[data-testid='generate-success']", { timeout: 60_000 });
}
