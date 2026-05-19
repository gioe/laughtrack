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
