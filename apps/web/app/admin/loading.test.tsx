import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import AdminLoading from "./loading";

describe("AdminLoading", () => {
    it("renders an accessible admin navigation loading state", () => {
        const markup = renderToStaticMarkup(<AdminLoading />);

        expect(markup).toContain('role="status"');
        expect(markup).toContain("Loading admin section");
    });
});
