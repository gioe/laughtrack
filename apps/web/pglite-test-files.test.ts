import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { PGLITE_TEST_FILES } from "./pglite-test-files";

const PGLITE_IMPORT = /^import\s+.*from\s+["']@electric-sql\/pglite["'];?$/m;
const TEST_FILE_PATTERN = /\.test\.tsx?$/;
const IGNORED_DIRECTORIES = new Set([".git", ".next", "node_modules"]);

async function collectTestFiles(directory: string): Promise<string[]> {
    const entries = await readdir(directory, { withFileTypes: true });
    const files = await Promise.all(
        entries.map(async (entry): Promise<string[]> => {
            const entryPath = path.join(directory, entry.name);
            if (entry.isDirectory()) {
                return IGNORED_DIRECTORIES.has(entry.name)
                    ? []
                    : collectTestFiles(entryPath);
            }
            return TEST_FILE_PATTERN.test(entry.name) ? [entryPath] : [];
        }),
    );
    return files.flat();
}

describe("PGlite Vitest project inventory", () => {
    it("serializes every test file that boots PGlite", async () => {
        const root = process.cwd();
        const testFiles = await collectTestFiles(root);
        const importers = (
            await Promise.all(
                testFiles.map(async (file) => ({
                    file,
                    source: await readFile(file, "utf8"),
                })),
            )
        )
            .filter(({ source }) => PGLITE_IMPORT.test(source))
            .map(({ file }) =>
                path.relative(root, file).split(path.sep).join("/"),
            )
            .sort();

        expect(importers).toEqual([...PGLITE_TEST_FILES].sort());
    });
});
