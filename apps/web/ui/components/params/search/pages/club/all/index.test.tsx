/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryProperty } from "@/objects/enum";
import ClubSearchBar from "./index";

const { mockGetTypedParam, mockSetTypedParam } = vi.hoisted(() => ({
    mockGetTypedParam: vi.fn(),
    mockSetTypedParam: vi.fn(),
}));

vi.mock("@/contexts/StyleProvider", () => ({
    useStyleContext: () => ({
        getCurrentStyles: () => ({
            iconTextColor: "text-test",
            inputTextColor: "input-test",
        }),
    }),
}));

vi.mock("@/hooks/useUrlParams", () => ({
    useUrlParams: () => ({
        getTypedParam: mockGetTypedParam,
        setTypedParam: mockSetTypedParam,
    }),
}));

vi.mock("../../../components/textInput", () => ({
    default: (props: { value: string; onChange: (value: string) => void }) => (
        <button type="button" onClick={() => props.onChange("Comedy Cellar")}>
            {props.value}
        </button>
    ),
}));

vi.mock("../../../components/area", () => ({
    default: (props: {
        value: { zipCode: string | null; distance: string | null };
        onZipcodeInput: (value: string) => void;
        onDistanceSelection: (value: string) => void;
    }) => (
        <div>
            <span data-testid="location-value">
                {props.value.zipCode}:{props.value.distance}
            </span>
            <button type="button" onClick={() => props.onZipcodeInput("10001")}>
                Change ZIP
            </button>
            <button
                type="button"
                onClick={() => props.onDistanceSelection("25")}
            >
                Change radius
            </button>
            <button type="button" onClick={() => props.onZipcodeInput("")}>
                Clear ZIP
            </button>
        </div>
    ),
}));

beforeEach(() => {
    vi.clearAllMocks();
    mockGetTypedParam.mockImplementation((key: QueryProperty) => {
        if (key === QueryProperty.Club) return "Cellar";
        if (key === QueryProperty.Zip) return "10002";
        if (key === QueryProperty.Distance) return "10";
        return undefined;
    });
});

afterEach(() => {
    cleanup();
});

describe("ClubSearchBar location filtering", () => {
    it("renders ZIP and radius from URL search state", () => {
        render(<ClubSearchBar />);

        expect(screen.getByTestId("location-value").textContent).toBe(
            "10002:10",
        );
    });

    it("updates and clears the ZIP search origin", () => {
        render(<ClubSearchBar />);

        fireEvent.click(screen.getByRole("button", { name: "Change ZIP" }));
        expect(mockSetTypedParam).toHaveBeenCalledWith(
            QueryProperty.Zip,
            "10001",
        );

        fireEvent.click(screen.getByRole("button", { name: "Clear ZIP" }));
        expect(mockSetTypedParam).toHaveBeenCalledWith(QueryProperty.Zip, "");
    });

    it("updates the radius while keeping the same ZIP origin", () => {
        render(<ClubSearchBar />);

        fireEvent.click(screen.getByRole("button", { name: "Change radius" }));

        expect(mockSetTypedParam).toHaveBeenCalledWith(
            QueryProperty.Distance,
            "25",
        );
        expect(screen.getByTestId("location-value").textContent).toContain(
            "10002",
        );
    });
});
