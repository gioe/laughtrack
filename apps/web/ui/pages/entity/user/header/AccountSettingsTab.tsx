"use client";

import React from "react";
import { Save } from "lucide-react";

interface AccountSettingsTabProps {
    email: string | null | undefined;
    zipCode: string;
    isDirty: boolean;
    isLoading: boolean;
    onChange: (value: string) => void;
    onSave: () => void;
}

const AccountSettingsTab = ({
    email,
    zipCode,
    isDirty,
    isLoading,
    onChange,
    onSave,
}: AccountSettingsTabProps) => {
    return (
        <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Account Settings</h3>
                {isDirty && (
                    <button
                        onClick={onSave}
                        disabled={isLoading}
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
                        value={email ?? ""}
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
                        value={zipCode}
                        onChange={(e) => onChange(e.target.value)}
                        className="w-full px-3 py-2 border rounded-md focus:ring-copper focus:border-copper"
                        placeholder="Enter your zip code"
                    />
                </div>
            </div>
        </div>
    );
};

export default AccountSettingsTab;
