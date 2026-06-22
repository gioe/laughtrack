"use client";

import React, { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { Loader2 } from "lucide-react";
import UserHeroBanner from "./UserHeroBanner";
import UserTabNav from "./UserTabNav";
import FavoritesTab from "./FavoritesTab";
import NotificationCenterTab from "./NotificationCenterTab";
import NotificationsTab from "./NotificationsTab";
import AccountSettingsTab from "./AccountSettingsTab";
import { useProfileForm } from "./useProfileForm";

interface UserDetailHeaderProps {
    profile: UserProfileInterface;
}

type TabType = "favorites" | "notifications" | "account";

const VALID_TABS: readonly TabType[] = [
    "favorites",
    "notifications",
    "account",
];

const parseTab = (value: string | null): TabType =>
    VALID_TABS.includes(value as TabType) ? (value as TabType) : "favorites";

const UserDetailHeader = ({ profile }: UserDetailHeaderProps) => {
    const { mv, springs } = useMotionProps();
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const activeTab = parseTab(searchParams?.get("tab") ?? null);

    // Unread badge on the Notifications tab. Sourced from the /me launch fetch
    // (notificationsUnreadCount); cleared the moment the center marks seen.
    const [notificationsUnread, setNotificationsUnread] = useState(0);

    useEffect(() => {
        let cancelled = false;
        fetch("/api/v1/me", { credentials: "same-origin" })
            .then((res) => (res.ok ? res.json() : null))
            .then((body) => {
                if (!cancelled && body?.data) {
                    setNotificationsUnread(
                        body.data.notificationsUnreadCount ?? 0,
                    );
                }
            })
            .catch(() => {});
        return () => {
            cancelled = true;
        };
    }, []);

    const handleNotificationsSeen = useCallback(() => {
        setNotificationsUnread(0);
    }, []);

    const handleTabChange = (next: TabType) => {
        const params = new URLSearchParams(searchParams?.toString() ?? "");
        if (next === "favorites") {
            params.delete("tab");
        } else {
            params.set("tab", next);
        }
        const qs = params.toString();
        router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    };

    const { fields, dirtyFields, isLoading, handleFieldChange, handleSave } =
        useProfileForm(profile);

    return (
        <div className="max-w-7xl mx-auto">
            <UserHeroBanner
                name={profile.name}
                email={profile.email}
                image={profile.image}
            />

            <UserTabNav
                activeTab={activeTab}
                onTabChange={handleTabChange}
                notificationsUnread={notificationsUnread}
            />

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <AnimatePresence mode="wait">
                    {activeTab === "favorites" && (
                        <motion.div
                            key="favorites"
                            initial={{ opacity: 0, y: mv(20) }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: mv(-20) }}
                            transition={springs.contentEntrance}
                        >
                            <FavoritesTab />
                        </motion.div>
                    )}

                    {activeTab === "notifications" && (
                        <motion.div
                            key="notifications"
                            initial={{ opacity: 0, y: mv(20) }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: mv(-20) }}
                            transition={springs.contentEntrance}
                            className="max-w-2xl space-y-6"
                        >
                            <NotificationCenterTab
                                onSeen={handleNotificationsSeen}
                            />
                            <NotificationsTab
                                emailOptin={fields.emailOptin}
                                isDirty={!!dirtyFields.emailOptin}
                                isLoading={isLoading}
                                onChange={(v) =>
                                    handleFieldChange("emailOptin", v)
                                }
                                onSave={handleSave}
                            />
                        </motion.div>
                    )}

                    {activeTab === "account" && (
                        <motion.div
                            key="account"
                            initial={{ opacity: 0, y: mv(20) }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: mv(-20) }}
                            transition={springs.contentEntrance}
                            className="max-w-2xl"
                        >
                            <AccountSettingsTab
                                email={profile.email}
                                zipCode={fields.zipCode}
                                isDirty={!!dirtyFields.zipCode}
                                isLoading={isLoading}
                                onChange={(v) =>
                                    handleFieldChange("zipCode", v)
                                }
                                onSave={handleSave}
                            />
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {isLoading && (
                <div className="z-10 absolute inset-0 flex items-center justify-center bg-black/50 rounded-lg">
                    <Loader2 className="w-8 h-8 text-copper animate-spin" />
                </div>
            )}
        </div>
    );
};

export default UserDetailHeader;
