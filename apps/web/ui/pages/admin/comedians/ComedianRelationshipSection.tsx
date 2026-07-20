"use client";

import type { ReactNode } from "react";
import { ComedianEditorSection } from "./ComedianEditorSection";

type Props = {
    rowId: number;
    open: boolean;
    onToggle: () => void;
    childCount: number;
    children: ReactNode;
};

export function ComedianRelationshipSection({ childCount, ...props }: Props) {
    return (
        <ComedianEditorSection
            {...props}
            idPrefix="relationship"
            title={`Relationship (${childCount.toLocaleString()} children)`}
            contentClassName="space-y-3 border-t border-copper/15 p-3"
        />
    );
}
