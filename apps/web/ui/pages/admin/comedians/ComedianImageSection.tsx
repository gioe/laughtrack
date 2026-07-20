"use client";

import type { ReactNode } from "react";
import { ComedianEditorSection } from "./ComedianEditorSection";

type Props = {
    rowId: number;
    open: boolean;
    onToggle: () => void;
    children: ReactNode;
};

export function ComedianImageSection(props: Props) {
    return (
        <ComedianEditorSection
            {...props}
            idPrefix="images"
            title="Current image"
            contentClassName="border-t border-copper/15 p-3"
        />
    );
}
