import { ChevronDown, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
    groupKey: string;
    title: string;
    subtitle: string;
    summary: string;
    collapsed: boolean;
    onToggle: (groupKey: string) => void;
    children: ReactNode;
};

export function AdminPodcastHostshipReviewGroupFrame({
    groupKey,
    title,
    subtitle,
    summary,
    collapsed,
    onToggle,
    children,
}: Props) {
    const panelId = `podcast-review-group-${groupKey}`;

    return (
        <section className="overflow-hidden rounded-md border border-copper/20 bg-white">
            <header className="border-b border-copper/20 bg-cedar px-4 py-3 text-white">
                <button
                    type="button"
                    aria-expanded={!collapsed}
                    aria-controls={panelId}
                    onClick={() => onToggle(groupKey)}
                    className="flex w-full min-w-0 items-start gap-3 text-left"
                >
                    <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-white/30 bg-white/10">
                        {collapsed ? (
                            <ChevronRight className="h-4 w-4" />
                        ) : (
                            <ChevronDown className="h-4 w-4" />
                        )}
                    </span>
                    <span className="min-w-0">
                        <span className="block font-urbanist-bold text-h3 leading-tight">
                            {title}
                        </span>
                        <span className="mt-1 block font-dmSans text-caption text-white/85">
                            {subtitle} · {summary}
                        </span>
                    </span>
                </button>
            </header>
            <div
                id={panelId}
                hidden={collapsed}
                className={`${collapsed ? "hidden" : ""} grid gap-4 p-4`}
            >
                {children}
            </div>
        </section>
    );
}
