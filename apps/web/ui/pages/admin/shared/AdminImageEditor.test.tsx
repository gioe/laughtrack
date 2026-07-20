/**
 * @vitest-environment happy-dom
 */

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminImageEditor } from "./AdminImageEditor";

type EditorProps = ComponentProps<typeof AdminImageEditor>;

function makeProps(overrides: Partial<EditorProps> = {}): EditorProps {
    return {
        id: "thumbnail-42",
        title: "Thumbnail",
        emptyClassName: "empty-preview",
        urlInput: {
            label: "Thumbnail image URL",
            ariaLabel: "Club thumbnail image URL",
            value: "",
            placeholder: "https://example.com/image.png",
            saveAriaLabel: "Save club thumbnail URL",
            canSave: false,
            onChange: vi.fn(),
            onSave: vi.fn(),
        },
        fileInput: {
            ariaLabel: "Upload club thumbnail file",
            chooseLabel: "Choose thumbnail file",
            guidance: "1:1 square, at least 600x600",
            stagedFile: null,
            pendingLabel: "Pending thumbnail",
            pendingAlt: "Comedy club pending thumbnail",
            previewClassName: "staged-preview",
            onSelect: vi.fn(),
            onPublish: vi.fn(),
            onDiscard: vi.fn(),
        },
        disabled: false,
        ...overrides,
    };
}

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

describe("AdminImageEditor", () => {
    it("forwards selected files and resets the native input", () => {
        const onSelect = vi.fn();
        const props = makeProps({
            fileInput: { ...makeProps().fileInput, onSelect },
        });
        render(<AdminImageEditor {...props} />);

        const input = screen.getByLabelText(
            "Upload club thumbnail file",
        ) as HTMLInputElement;
        const file = new File(["image"], "club.png", {
            type: "image/png",
        });
        Object.defineProperty(input, "files", {
            configurable: true,
            value: [file],
        });
        fireEvent.change(input);

        expect(onSelect).toHaveBeenCalledWith(file);
        expect(input.value).toBe("");
    });

    it("creates and revokes staged preview object URLs", () => {
        const createObjectURL = vi
            .spyOn(URL, "createObjectURL")
            .mockReturnValueOnce("blob:first")
            .mockReturnValueOnce("blob:second");
        const revokeObjectURL = vi
            .spyOn(URL, "revokeObjectURL")
            .mockImplementation(() => undefined);
        const first = new File(["first"], "first.png", {
            type: "image/png",
        });
        const second = new File(["second"], "second.png", {
            type: "image/png",
        });
        const base = makeProps();
        const { rerender, unmount } = render(
            <AdminImageEditor
                {...base}
                fileInput={{ ...base.fileInput, stagedFile: first }}
            />,
        );

        expect(
            screen
                .getByAltText("Comedy club pending thumbnail")
                .getAttribute("src"),
        ).toBe("blob:first");
        rerender(
            <AdminImageEditor
                {...base}
                fileInput={{ ...base.fileInput, stagedFile: second }}
            />,
        );
        expect(revokeObjectURL).toHaveBeenCalledWith("blob:first");
        expect(createObjectURL).toHaveBeenCalledTimes(2);

        unmount();
        expect(revokeObjectURL).toHaveBeenCalledWith("blob:second");
    });

    it("forwards discard and remove actions", () => {
        vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:preview");
        vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
        const onDiscard = vi.fn();
        const onRemove = vi.fn();
        const base = makeProps();
        render(
            <AdminImageEditor
                {...base}
                fileInput={{
                    ...base.fileInput,
                    stagedFile: new File(["image"], "club.png"),
                    onDiscard,
                }}
                remove={{
                    visible: true,
                    label: "Remove thumbnail",
                    onRemove,
                }}
            />,
        );

        fireEvent.click(screen.getByRole("button", { name: "Discard" }));
        fireEvent.click(
            screen.getByRole("button", { name: "Remove thumbnail" }),
        );
        expect(onDiscard).toHaveBeenCalledOnce();
        expect(onRemove).toHaveBeenCalledOnce();
    });

    it("announces error and success feedback", () => {
        const props = makeProps({
            status: { kind: "error", message: "Image is too small." },
        });
        const { rerender } = render(<AdminImageEditor {...props} />);

        expect(screen.getByRole("alert").textContent).toBe(
            "Image is too small.",
        );
        rerender(
            <AdminImageEditor
                {...props}
                status={{ kind: "ok", message: "Thumbnail staged." }}
            />,
        );
        expect(screen.getByRole("status").textContent).toBe(
            "Thumbnail staged.",
        );
    });
});
