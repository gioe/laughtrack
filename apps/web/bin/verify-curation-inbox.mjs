/** Isolated browser contracts: real UI, stateful test API, no production connections.
 * Run: node bin/verify-curation-inbox.mjs. Screenshots go to /tmp/curation-inbox-*.png.
 * SQL decision invariants are separately exercised by hostRelationships.test.ts.
 */
import { createServer } from "vite";
import { chromium } from "playwright";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../", import.meta.url));
const fixture = `import React from 'react';import {createRoot} from 'react-dom/client';import Workspace from '/ui/pages/admin/reviews/CurationWorkspace.tsx';import '/app/globals.css';createRoot(document.getElementById('root')).render(React.createElement(Workspace,{initialFilters:Object.fromEntries(new URLSearchParams(location.search))}));`;
const server = await createServer({
  root,
  configFile: false,
  esbuild: { jsx: "automatic" },
  resolve: { alias: { "@": root } },
  server: { host: "127.0.0.1", port: 0 },
  plugins: [
    {
      name: "isolated-curation-browser",
      configureServer(s) {
        s.middlewares.use((req, res, next) => {
          if (req.url?.startsWith("/admin/reviews")) {
            res.setHeader("Content-Type", "text/html");
            res.end(
              '<!doctype html><html><head><style>:root{--font-dmSans:Arial;--font-urbanist:Arial}</style><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><main style="padding:20px;max-width:1400px;margin:auto"><h1 style="font: bold 28px sans-serif;margin-bottom:20px">Review Inbox</h1><div id="root"></div></main><script type="module" src="/@id/virtual:curation-fixture"></script></body></html>',
            );
            return;
          }
          next();
        });
      },
      resolveId(id) {
        if (id === "virtual:curation-fixture") return "\0" + id;
      },
      load(id) {
        if (id === "\0virtual:curation-fixture") return fixture;
      },
    },
  ],
});
await server.listen();
const port = server.httpServer.address().port;
const browser = await chromium.launch({ headless: true });
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({
      viewport: { width, height: 1000 },
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    let item = {
      target: {
        type: "entity",
        id: "podcast-test",
        kind: "podcast",
        scope: "entity",
      },
      label: "The Example Comedy Podcast",
      state: "pending",
      version: 0,
      recordId: 10,
      keys: [
        {
          namespace: "podcast-feed-url:v1",
          scope: "global",
          value: "https://example.org/comedy/feed.xml",
          key_type: "feed_url",
        },
      ],
      observations: [
        {
          id: "evidence",
          source: "Official podcast feed",
          source_key: "episode-credits",
          recorded_at: "2026-10-18T12:00:00Z",
          evidence: {
            title: "Episode credits",
            sourceUrl: "https://example.org/podcast",
            description: "Hosted by Alex Example and Robin Example.",
          },
        },
      ],
      decisions: [],
      requests: [],
      matches: [],
      reconciliations: [],
      candidateId: null,
    };
    const receipts = new Map();
    let writes = 0;
    await page.route("**/api/admin/**", async (route) => {
      const req = route.request(),
        u = new URL(req.url());
      let data;
      if (u.pathname.endsWith("/inbox"))
        data = u.searchParams.has("id")
          ? item
          : { items: [item], hasMore: false };
      else if (req.method() === "GET")
        data = receipts.get(u.searchParams.get("requestId")) ?? {
          status: "pending",
        };
      else {
        const body = req.postDataJSON(),
          cmd = body.command;
        if (body.operation === "preview")
          data = {
            available: true,
            effects: [
              cmd.action === "block"
                ? "Block only this podcast identity and known feed identifiers; future discoveries remain blocked."
                : "Change only this relationship or scoped identity.",
            ],
            boundaries: "Other entities and relationships remain unchanged.",
            restoration:
              "Restoration reopens review; it does not approve or publish.",
          };
        else if (body.operation === "submit") {
          if (receipts.has(cmd.requestId)) data = receipts.get(cmd.requestId);
          else {
            writes++;
            const before = item.state;
            item.state =
              cmd.action === "block"
                ? "blocked"
                : cmd.action === "restore"
                  ? item.target.type === "entity"
                    ? "pending"
                    : "proposed"
                  : cmd.action === "confirm"
                    ? "confirmed"
                    : cmd.action === "sever"
                      ? "severed"
                      : "approved";
            item.version++;
            item.decisions.unshift({
              id: String(writes),
              action: cmd.action,
              actor: "isolated-reviewer",
              reason: cmd.reason,
              created_at: new Date().toISOString(),
              before_state: before,
              after_state: item.state,
            });
            data = { status: "applied" };
            receipts.set(cmd.requestId, data);
          }
        } else throw Error("Unexpected test operation");
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(data),
      });
    });
    const goto = async (view) => {
      await page.goto(`http://127.0.0.1:${port}/admin/reviews?view=${view}`, {
        waitUntil: "load",
      });
      await page
        .getByRole("heading", { name: item.label, exact: true })
        .waitFor();
    };
    const decide = async (label) => {
      await page
        .getByLabel("Decision reason", { exact: true })
        .fill("Verified official credits in isolated browser test");
      await page.getByRole("button", { name: label, exact: true }).click();
      await page.getByRole("region", { name: "Decision preview" }).waitFor();
      await page
        .getByRole("button", { name: "Apply decision", exact: true })
        .click();
      await page.getByText(/Decision applied/).waitFor();
    };
    await goto("intake");
    await decide("Reject and block future intake");
    await page
      .getByRole("button", { name: "Restore for review", exact: true })
      .waitFor();
    assert.equal(item.state, "blocked");
    // Rediscovery refreshes evidence, never changes the stored decision.
    item.observations.push({
      ...item.observations[0],
      id: "rediscovered",
      source: "Second discovery source",
    });
    if (width === 390)
      await page
        .getByRole("button", { name: "Queue filters", exact: true })
        .click();
    await page
      .getByRole("button", { name: "Refresh queue", exact: true })
      .click();
    if (width === 390)
      await page
        .getByRole("button", { name: "Queue filters", exact: true })
        .click();
    await page.getByText(/Second discovery source/).waitFor();
    await page
      .getByRole("button", { name: "Restore for review", exact: true })
      .waitFor();
    assert.equal(writes, 1);
    await page.screenshot({
      path: `/tmp/curation-inbox-intake-${width}.png`,
      fullPage: true,
    });
    await decide("Restore for review");
    await page
      .getByRole("button", { name: "Approve intake", exact: true })
      .waitFor();
    assert.equal(item.state, "pending");
    item = {
      ...item,
      target: { type: "relationship", id: "host-test", kind: "host_of" },
      label: "Alex Example → The Example Comedy Podcast",
      state: "proposed",
      version: 0,
      sourceLabel: "Alex Example",
      targetLabel: "The Example Comedy Podcast",
      sourceRecordId: 1,
      targetRecordId: 10,
      decisions: [],
    };
    await goto("relationships");
    await decide("Establish relationship");
    await page
      .getByRole("button", { name: "Sever relationship", exact: true })
      .waitFor();
    assert.equal(item.state, "confirmed");
    await decide("Sever relationship");
    await page
      .getByRole("button", { name: "Restore for review", exact: true })
      .waitFor();
    assert.equal(item.state, "severed");
    await page.screenshot({
      path: `/tmp/curation-inbox-relationship-${width}.png`,
      fullPage: true,
    });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
      "Horizontal overflow",
    );
    await page.getByLabel("Decision reason", { exact: true }).fill("j");
    assert.equal(
      await page
        .getByRole("heading", { name: item.label, exact: true })
        .count(),
      1,
    );
    await page.getByRole("heading", { name: item.label, exact: true }).focus();
    await page.keyboard.press("j");
    await page
      .getByRole("heading", { name: "Select a review", exact: true })
      .waitFor();
    assert.equal(writes, 4);
    if (width === 390) {
      await page.getByRole("button", { name: /Review queue/ }).click();
      assert.equal(
        await page
          .getByRole("button", { name: /Review queue/ })
          .getAttribute("aria-expanded"),
        "true",
      );
    }
    assert.deepEqual(errors, []);
    await context.close();
    console.log(
      `PASS ${width}px: reject / rediscover / restore, establish / sever, keyboard skip, no overflow or browser errors.`,
    );
  }
} finally {
  await browser.close();
  await server.close();
}
