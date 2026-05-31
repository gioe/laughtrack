import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
    esbuild: {
        jsx: "automatic",
    },
    test: {
        environment: "node",
        exclude: ["**/node_modules/**", "**/e2e/**"],
        env: {
            BUNNYCDN_CDN_HOST: "test.b-cdn.net",
        },
        // PGlite migration tests bootstrap an in-process Postgres WASM in
        // beforeAll; under the full 113-file suite's CPU contention that can
        // exceed vitest's 10s default and surface as misleading "hook timeout"
        // failures unrelated to the code under test.
        hookTimeout: 30000,
        // Route handlers log to console.error in their catch blocks, and many
        // route tests deliberately exercise those error paths. By default
        // vitest forwards every worker console call to the main process over
        // the `onUserConsoleLog` RPC; when a log is still in flight as the
        // worker tears down, the run dies with
        //   EnvironmentTeardownError: Closing rpc while onUserConsoleLog was pending
        // surfacing non-deterministically in whichever file happened to be
        // mid-teardown. Disabling the intercept writes console output straight
        // to stdout/stderr synchronously, eliminating that RPC and the race
        // (the commit-time test gate flaked ~1/8 full-suite runs before this).
        disableConsoleIntercept: true,
        // Auto-run vi.unstubAllGlobals() before every test so a file that
        // stubs a global (most commonly global.fetch via vi.stubGlobal) can
        // never leak that stub into a later file. Without this, a suite that
        // stubs fetch but forgets afterEach(vi.unstubAllGlobals) leaves the
        // stubbed fetch installed for whichever file vitest runs next in the
        // same worker — and a single-use Response body from that stale stub
        // throws "Body has already been read" nondeterministically in the full
        // suite (app/api/admin/podcast-ownership-reviews/route.test.ts was the
        // offender; TASK-2534). The unstub runs as an internal beforeEach that
        // fires *before* user beforeEach hooks, so every suite that re-stubs in
        // beforeEach or per-test (all of ours do) is unaffected.
        unstubGlobals: true,
    },
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "."),
            "server-only": path.resolve(
                __dirname,
                "vitest-server-only-stub.ts",
            ),
        },
    },
});
