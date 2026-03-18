"use client";

import React from "react";
import { Star, Bell, Settings } from "lucide-react";

type TabType = "favorites" | "notifications" | "account";

interface UserTabNavProps {
    activeTab: TabType;
    onTabChange: (tab: TabType) => void;
}

const tabs = [
    { id: "favorites" as TabType, label: "Favorite Comedians", icon: Star },
    { id: "notifications" as TabType, label: "Notifications", icon: Bell },
    { id: "account" as TabType, label: "Account Settings", icon: Settings },
];

const UserTabNav = ({ activeTab, onTabChange }: UserTabNavProps) => {
    return (
        <div className="border-b border-gray-200 mt-6">
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
                                            : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                                    }
                                `}
                            >
                                <Icon className="w-4 h-4" />
                                {tab.label}
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default UserTabNav;
