"use client";

import type { ReactNode } from "react";
import { ComedianEditorSection } from "./ComedianEditorSection";

type Props = {
    rowId: number;
    open: boolean;
    onToggle: () => void;
    attributedCount: number;
    pendingCount: number;
    children: ReactNode;
};

export function ComedianPodcastSection({
    attributedCount,
    pendingCount,
    ...props
}: Props) {
    return (
        <ComedianEditorSection
            {...props}
            idPrefix="podcasts"
            title={`Podcast (${attributedCount.toLocaleString()} attributed, ${pendingCount.toLocaleString()} pending)`}
            contentClassName="space-y-5 border-t border-copper/15 p-3"
        />
    );
}
