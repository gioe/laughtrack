"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { Loader2 } from "lucide-react";
import UserHeroBanner from "./UserHeroBanner";
import UserTabNav from "./UserTabNav";
import FavoritesTab from "./FavoritesTab";
import NotificationsTab from "./NotificationsTab";
import AccountSettingsTab from "./AccountSettingsTab";
import { useProfileForm } from "./useProfileForm";

interface UserDetailHeaderProps {
    profile: UserProfileInterface;
}

type TabType = "favorites" | "notifications" | "account";

const UserDetailHeader = ({ profile }: UserDetailHeaderProps) => {
    const { mv } = useMotionProps();
    const [activeTab, setActiveTab] = useState<TabType>("favorites");
    const { fields, dirtyFields, isLoading, handleFieldChange, handleSave } =
        useProfileForm(profile);

    return (
        <div className="max-w-7xl mx-auto">
            <UserHeroBanner
                name={profile.name}
                email={profile.email}
                image={profile.image}
            />

            <UserTabNav activeTab={activeTab} onTabChange={setActiveTab} />

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <AnimatePresence mode="wait">
                    {activeTab === "favorites" && (
                        <motion.div
                            key="favorites"
                            initial={{ opacity: 0, y: mv(20) }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: mv(-20) }}
                        >
                            <FavoritesTab userId={profile.userId!} />
                        </motion.div>
                    )}

                    {activeTab === "notifications" && (
                        <motion.div
                            key="notifications"
                            initial={{ opacity: 0, y: mv(20) }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: mv(-20) }}
                            className="max-w-2xl"
                        >
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
                <div className="z-10 absolute inset-0 flex items-center justify-center bg-white/50 rounded-lg">
                    <Loader2 className="w-8 h-8 text-copper animate-spin" />
                </div>
            )}
        </div>
    );
};

export default UserDetailHeader;
