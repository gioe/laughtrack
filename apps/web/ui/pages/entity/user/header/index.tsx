"use client";

import toast from "react-hot-toast";
import React, { useState } from "react";
import { Save, Bell, Settings, Star } from "lucide-react";
import { makeRequest } from "@/util/actions/makeRequest";
import { APIRoutePath, RestAPIAction } from "@/objects/enum";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { Loader2 } from "lucide-react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { useMotionProps } from "@/hooks";
import FavoriteComediansGrid from "@/ui/components/grid/favoriteComedians";

interface UserDetailHeaderProps {
    profile: UserProfileInterface;
}

type TabType = "favorites" | "notifications" | "account";

interface EditableFieldsState {
    emailOptin: boolean;
    zipCode: string;
}

const UserDetailHeader = ({ profile }: UserDetailHeaderProps) => {
    const { mv, mt, prefersReducedMotion } = useMotionProps();
    const [isLoading, setIsLoading] = useState(false);
    const [imageLoaded, setImageLoaded] = useState(false);
    const [imageError, setImageError] = useState(false);
    const [activeTab, setActiveTab] = useState<TabType>("favorites");
    const [fields, setFields] = useState<EditableFieldsState>({
        emailOptin: profile.emailOptin ?? false,
        zipCode: profile.zipCode ?? "",
    });
    const [dirtyFields, setDirtyFields] = useState<
        Partial<EditableFieldsState>
    >({});

    const handleFieldChange = (
        field: keyof EditableFieldsState,
        value: string | boolean,
    ) => {
        setFields((prev) => ({ ...prev, [field]: value }));
        setDirtyFields((prev) => ({
            ...prev,
            [field]: value !== (profile[field] ?? ""),
        }));
    };

    const handleSave = async () => {
        if (Object.keys(dirtyFields).length === 0) return;

        setIsLoading(true);
        try {
            const route = APIRoutePath.Profile + `/${profile.userId}`;
            await makeRequest(route, {
                method: RestAPIAction.PUT,
                body: {
                    zipCode: fields.zipCode,
                    emailOptin: fields.emailOptin,
                },
            });

            // Update the profile reference with new values
            profile.zipCode = fields.zipCode;
            profile.emailOptin = fields.emailOptin;
            setDirtyFields({});
            toast.success("Updated successfully");
        } catch (error) {
            console.error("Failed to update profile:", error);
            toast.error("Something went wrong");
            // Reset fields to original values
            setFields({
                emailOptin: profile.emailOptin ?? false,
                zipCode: profile.zipCode ?? "",
            });
            setDirtyFields({});
        } finally {
            setIsLoading(false);
        }
    };

    const tabs = [
        { id: "favorites", label: "Favorite Comedians", icon: Star },
        { id: "notifications", label: "Notifications", icon: Bell },
        { id: "account", label: "Account Settings", icon: Settings },
    ];

    return (
        <div className="max-w-7xl mx-auto">
            {/* Hero Image Section */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={mt({ duration: 0.4 })}
                className="relative w-full h-48 md:h-64 overflow-hidden rounded-xl"
            >
                {/* Gradient fallback background */}
                <div className="absolute inset-0 bg-gradient-to-br from-copper/60 via-cedar/40 to-stone-800" />

                {/* Hero image */}
                {profile.image && !imageError && (
                    <>
                        <Image
                            src={profile.image}
                            alt={profile.name || "Profile"}
                            fill
                            className={`object-cover object-center transition-opacity duration-500 ${
                                imageLoaded ? "opacity-100" : "opacity-0"
                            }`}
                            onError={() => setImageError(true)}
                            onLoad={() => setImageLoaded(true)}
                            priority
                            sizes="(max-width: 768px) 100vw, 1280px"
                        />
                        {/* Skeleton pulse during image load */}
                        {!imageLoaded && (
                            <div
                                className={`absolute inset-0 bg-stone-700${!prefersReducedMotion ? " animate-pulse" : ""}`}
                            />
                        )}
                        {/* Overlay gradient — only when image is present */}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
                    </>
                )}

                {/* Name + email overlaid at bottom */}
                <div className="absolute bottom-0 left-0 right-0 p-6">
                    <motion.h1
                        initial={{ opacity: 0, y: mv(20) }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={mt({ duration: 0.3, delay: mv(0.1) })}
                        className="text-3xl md:text-4xl font-bold text-white drop-shadow-lg font-gilroy-bold"
                    >
                        {profile.name || "Comedy Fan"}
                    </motion.h1>
                    <motion.p
                        initial={{ opacity: 0, y: mv(10) }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={mt({ duration: 0.3, delay: mv(0.2) })}
                        className="text-white/80"
                    >
                        {profile.email}
                    </motion.p>
                </div>
            </motion.div>

            {/* Tabs */}
            <div className="border-b border-gray-200 mt-6">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex space-x-8">
                        {tabs.map((tab) => {
                            const Icon = tab.icon;
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() =>
                                        setActiveTab(tab.id as TabType)
                                    }
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

            {/* Tab Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <AnimatePresence mode="wait">
                    {activeTab === "favorites" && (
                        <motion.div
                            key="favorites"
                            initial={{ opacity: 0, y: mv(20) }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: mv(-20) }}
                        >
                            <FavoriteComediansGrid userId={profile.userId!} />
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
                            <div className="bg-white rounded-xl p-6 shadow-sm">
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="text-lg font-semibold">
                                        Notification Preferences
                                    </h3>
                                    {dirtyFields.emailOptin && (
                                        <button
                                            onClick={handleSave}
                                            className="flex items-center gap-2 px-3 py-1.5 text-sm text-copper font-dmSans bg-white rounded-lg shadow-sm hover:shadow-md transition-all border border-copper"
                                        >
                                            <Save className="w-4 h-4" />
                                            Save Changes
                                        </button>
                                    )}
                                </div>
                                <div className="space-y-4">
                                    <div className="flex items-center space-x-3">
                                        <input
                                            checked={fields.emailOptin}
                                            type="checkbox"
                                            id="emailOptIn"
                                            className="h-4 w-4 rounded border-gray-300 text-copper focus:ring-copper"
                                            onChange={(e) =>
                                                handleFieldChange(
                                                    "emailOptin",
                                                    e.target.checked,
                                                )
                                            }
                                        />
                                        <label
                                            htmlFor="emailOptIn"
                                            className="text-gray-700"
                                        >
                                            Email me when comedians I follow
                                            have shows in my area
                                        </label>
                                    </div>
                                </div>
                            </div>
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
                            <div className="bg-white rounded-xl p-6 shadow-sm">
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="text-lg font-semibold">
                                        Account Settings
                                    </h3>
                                    {dirtyFields.zipCode && (
                                        <button
                                            onClick={handleSave}
                                            className="flex items-center gap-2 px-3 py-1.5 text-sm text-copper font-dmSans bg-white rounded-lg shadow-sm hover:shadow-md transition-all border border-copper"
                                        >
                                            <Save className="w-4 h-4" />
                                            Save Changes
                                        </button>
                                    )}
                                </div>
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Email address
                                        </label>
                                        <input
                                            type="email"
                                            value={profile.email}
                                            disabled={true}
                                            className="w-full px-3 py-2 border rounded-md disabled:bg-gray-50 disabled:text-gray-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Zip Code
                                        </label>
                                        <input
                                            type="text"
                                            value={fields.zipCode}
                                            onChange={(e) =>
                                                handleFieldChange(
                                                    "zipCode",
                                                    e.target.value,
                                                )
                                            }
                                            className="w-full px-3 py-2 border rounded-md focus:ring-copper focus:border-copper"
                                            placeholder="Enter your zip code"
                                        />
                                    </div>
                                </div>
                            </div>
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
