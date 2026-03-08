"use client";

import toast from "react-hot-toast";
import React, { useState } from "react";
import { Save, Bell, Settings, Star } from "lucide-react";
import { makeRequest } from "@/util/actions/makeRequest";
import { APIRoutePath, RestAPIAction } from "@/objects/enum";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { Loader2 } from "lucide-react";
import Image from "next/image";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
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
    const prefersReducedMotion = useReducedMotion();
    const [isLoading, setIsLoading] = useState(false);
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
            {/* Profile Header */}
            <div className="relative bg-gradient-to-r from-copper/10 to-brown-600/5 rounded-b-3xl p-8">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-6">
                        <div className="relative">
                            {profile.image ? (
                                <Image
                                    src={profile.image}
                                    alt="Profile"
                                    width={100}
                                    height={100}
                                    className="rounded-full border-4 border-white shadow-lg"
                                />
                            ) : (
                                <div className="w-24 h-24 rounded-full bg-gray-200 flex items-center justify-center">
                                    <span className="text-2xl text-gray-500">
                                        {profile.email?.[0]?.toUpperCase()}
                                    </span>
                                </div>
                            )}
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900 font-gilroy-bold">
                                {profile.name || "Comedy Fan"}
                            </h1>
                            <p className="text-gray-600">{profile.email}</p>
                        </div>
                    </div>
                </div>
            </div>

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
                            initial={{
                                opacity: 0,
                                y: prefersReducedMotion ? 0 : 20,
                            }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{
                                opacity: 0,
                                y: prefersReducedMotion ? 0 : -20,
                            }}
                        >
                            <FavoriteComediansGrid userId={profile.userId!} />
                        </motion.div>
                    )}

                    {activeTab === "notifications" && (
                        <motion.div
                            key="notifications"
                            initial={{
                                opacity: 0,
                                y: prefersReducedMotion ? 0 : 20,
                            }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{
                                opacity: 0,
                                y: prefersReducedMotion ? 0 : -20,
                            }}
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
                            initial={{
                                opacity: 0,
                                y: prefersReducedMotion ? 0 : 20,
                            }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{
                                opacity: 0,
                                y: prefersReducedMotion ? 0 : -20,
                            }}
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
