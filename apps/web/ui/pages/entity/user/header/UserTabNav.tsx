"use client";

import React from "react";
import { Star, Bell, Settings } from "lucide-react";

type TabType = "favorites" | "notifications" | "account";

interface UserTabNavProps {
    activeTab: TabType;
    onTabChange: (tab: TabType) => void;
    /** Unread notification count; renders a badge on the Notifications tab. */
    notificationsUnread?: number;
}

const tabs = [
    { id: "favorites" as TabType, label: "Favorites", icon: Star },
    { id: "notifications" as TabType, label: "Notifications", icon: Bell },
    { id: "account" as TabType, label: "Account Settings", icon: Settings },
];

const UserTabNav = ({
    activeTab,
    onTabChange,
    notificationsUnread = 0,
}: UserTabNavProps) => {
    return (
        <div className="border-b border-subtle mt-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex space-x-8">
                    {tabs.map((tab) => {
                        const Icon = tab.icon;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => onTabChange(tab.id)}
                                className={`
                                    flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm
                                    ${
                                        activeTab === tab.id
                                            ? "border-copper text-copper"
                                            : "border-transparent text-muted-foreground hover:text-foreground hover:border-strong"
                                    }
                                `}
                            >
                                <Icon className="w-4 h-4" />
                                {tab.label}
                                {tab.id === "notifications" &&
                                    notificationsUnread > 0 && (
                                        <span
                                            data-testid="notifications-unread-badge"
                                            className="ml-1 min-w-[18px] h-[18px] px-1 inline-flex items-center justify-center rounded-full bg-copper text-white text-[11px] font-semibold leading-none"
                                        >
                                            {notificationsUnread > 9
                                                ? "9+"
                                                : notificationsUnread}
                                        </span>
                                    )}
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default UserTabNav;
