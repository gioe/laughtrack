"use client";

import {
    Children,
    isValidElement,
    ReactElement,
    ReactNode,
    useState,
} from "react";

interface DetailTabsProps {
    ariaLabel: string;
    children: ReactNode;
    className?: string;
    defaultTabId?: string;
    panelClassName?: string;
    tabIdPrefix: string;
}

interface DetailTabProps {
    children: ReactNode;
    id: string;
    label: string;
    lazy?: boolean;
}

type DetailTabElement = ReactElement<DetailTabProps>;

export function DetailTab({ children }: DetailTabProps) {
    return <>{children}</>;
}

export default function DetailTabs({
    ariaLabel,
    children,
    className = "mt-2",
    defaultTabId,
    panelClassName = "",
    tabIdPrefix,
}: DetailTabsProps) {
    const tabs = Children.toArray(children).filter(
        (child): child is DetailTabElement =>
            isValidElement<DetailTabProps>(child),
    );
    const initialTabId = defaultTabId ?? tabs[0]?.props.id ?? "";
    const [activeTab, setActiveTab] = useState(initialTabId);
    const [activatedTabs, setActivatedTabs] = useState<Record<string, boolean>>(
        () => ({ [initialTabId]: true }),
    );

    if (tabs.length === 0) return null;
    if (tabs.length === 1) return <>{tabs[0].props.children}</>;

    const activateTab = (tabId: string) => {
        setActiveTab(tabId);
        setActivatedTabs((prev) => ({ ...prev, [tabId]: true }));
    };

    return (
        <section className={className}>
            <div className="sticky top-0 z-20 border-y border-gray-200 bg-white/95 backdrop-blur">
                <div
                    role="tablist"
                    aria-label={ariaLabel}
                    className="max-w-7xl mx-auto flex overflow-x-auto px-4 sm:px-6 md:px-8"
                >
                    {tabs.map((tab) => {
                        const selected = activeTab === tab.props.id;
                        return (
                            <button
                                key={tab.props.id}
                                id={`${tabIdPrefix}-tab-${tab.props.id}`}
                                type="button"
                                role="tab"
                                aria-selected={selected}
                                aria-controls={`${tabIdPrefix}-panel-${tab.props.id}`}
                                onClick={() => activateTab(tab.props.id)}
                                className={`whitespace-nowrap border-b-2 px-4 py-3 font-dmSans text-sm font-medium transition-colors ${
                                    selected
                                        ? "border-copper text-copper"
                                        : "border-transparent text-gray-600 hover:border-gray-300 hover:text-foreground"
                                }`}
                            >
                                {tab.props.label}
                            </button>
                        );
                    })}
                </div>
            </div>

            {tabs.map((tab) => {
                const selected = activeTab === tab.props.id;
                if (tab.props.lazy && !activatedTabs[tab.props.id]) {
                    return null;
                }

                return (
                    <div
                        key={tab.props.id}
                        id={`${tabIdPrefix}-panel-${tab.props.id}`}
                        role="tabpanel"
                        aria-labelledby={`${tabIdPrefix}-tab-${tab.props.id}`}
                        hidden={!selected}
                        className={panelClassName}
                    >
                        {tab.props.children}
                    </div>
                );
            })}
        </section>
    );
}
