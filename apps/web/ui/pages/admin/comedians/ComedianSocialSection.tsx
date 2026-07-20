"use client";

import type { ReactNode } from "react";
import { ComedianEditorSection } from "./ComedianEditorSection";

type Props = {
    rowId: number;
    open: boolean;
    onToggle: () => void;
    children: ReactNode;
};

export function ComedianSocialSection(props: Props) {
    return (
        <ComedianEditorSection
            {...props}
            idPrefix="social"
            title="Social media"
            contentClassName="grid gap-3 border-t border-copper/15 p-3"
        />
    );
}
