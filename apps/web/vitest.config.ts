import { defineConfig } from "vitest/config";
import path from "path";
import { PGLITE_TEST_FILES } from "./pglite-test-files";

const DEFAULT_EXCLUDE = ["**/node_modules/**", "**/e2e/**"];

export default defineConfig({
    esbuild: {
        jsx: "automatic",
    },
    test: {
        environment: "node",
        exclude: DEFAULT_EXCLUDE,
        env: {
            BUNNYCDN_CDN_HOST: "test.b-cdn.net",
        },
        // PGlite migration tests bootstrap an in-process Postgres WASM in
        // beforeAll; under the full 113-file suite's CPU contention that can
        // exceed vitest's 10s default and surface as misleading "hook timeout"
        // failures unrelated to the code under test.
        hookTimeout: 30000,
        // Same contention class as hookTimeout, for test bodies (TASK-2821):
        // render-heavy admin-manager tests run at 10-120ms in isolation but
        // inflate 25-50x when the full suite's forks compete with concurrent
        // workloads (parallel agent sessions each running their own commit
        // gate) — measured 2.2s per test with just two simultaneous suites,
        // and one AdminComedianManager test crossed vitest's 5s default
        // during a three-workload night and failed the gate with no code
        // defect (45ms isolated, passes on retry; no fake timers or
        // unawaited promises in the path). 15s keeps ~7x headroom over the
        // worst measured inflation while still failing genuine hangs fast
        // enough for the commit gate.
        testTimeout: 15000,
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
        // Each PGlite file boots an in-process PostgreSQL WASM runtime. Running
        // all of them across Vitest's default fork pool causes nonlinear CPU
        // and memory contention, so keep ordinary tests parallel and run only
        // the PGlite cohort sequentially after them.
        projects: [
            {
                extends: true,
                test: {
                    name: "unit",
                    exclude: [...DEFAULT_EXCLUDE, ...PGLITE_TEST_FILES],
                    sequence: { groupOrder: 0 },
                },
            },
            {
                extends: true,
                test: {
                    name: "pglite",
                    include: [...PGLITE_TEST_FILES],
                    fileParallelism: false,
                    sequence: { groupOrder: 1 },
                },
            },
        ],
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
