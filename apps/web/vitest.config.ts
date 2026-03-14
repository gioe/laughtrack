import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
    test: {
        environment: "node",
        exclude: ["**/node_modules/**", "**/e2e/**"],
        env: {
            BUNNYCDN_CDN_HOST: "test.b-cdn.net",
        },
    },
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "."),
        },
    },
});
