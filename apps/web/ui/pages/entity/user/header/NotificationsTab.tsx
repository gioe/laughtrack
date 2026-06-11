"use client";

import React from "react";
import { Save } from "lucide-react";

interface NotificationsTabProps {
    emailOptin: boolean;
    isDirty: boolean;
    isLoading: boolean;
    onChange: (value: boolean) => void;
    onSave: () => void;
}

const NotificationsTab = ({
    emailOptin,
    isDirty,
    isLoading,
    onChange,
    onSave,
}: NotificationsTabProps) => {
    return (
        <div className="bg-surface-elevated border border-subtle rounded-card p-6 shadow-card">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">
                    Notification Preferences
                </h3>
                {isDirty && (
                    <button
                        onClick={onSave}
                        disabled={isLoading}
                        className="flex items-center gap-2 px-3 py-1.5 text-copper font-dmSans bg-surface-muted rounded-lg shadow-card hover:shadow-floating transition-all border border-copper text-sm"
                    >
                        <Save className="w-4 h-4" />
                        Save Changes
                    </button>
                )}
            </div>
            <div className="space-y-4">
                <div className="flex items-center space-x-3">
                    <input
                        checked={emailOptin}
                        type="checkbox"
                        id="emailOptIn"
                        className="h-4 w-4 rounded border-gray-300 text-copper focus:ring-copper"
                        onChange={(e) => onChange(e.target.checked)}
                    />
                    <label htmlFor="emailOptIn" className="text-foreground/85">
                        Email me when comedians I follow have shows in my area
                    </label>
                </div>
            </div>
        </div>
    );
};

export default NotificationsTab;
