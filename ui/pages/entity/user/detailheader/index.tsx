"use client";

import React, { useState } from "react";
import { Pencil, Save } from "lucide-react";
import { UserInterface } from "@/objects/class/user/user.interface";

interface UserDetailHeaderProps {
    user: UserInterface;
}
const UserDetailHeader = ({ user }: UserDetailHeaderProps) => {
    const [isEditing, setIsEditing] = useState(false);
    const [email, setEmail] = useState(user.email);
    const [zipCode, setZipCode] = useState(user.zipCode);
    const [hasChanges, setHasChanges] = useState(false);

    const handleInputChange =
        (setter: (arg0: any) => void) => (e: { target: { value: any } }) => {
            setter(e.target.value);
            setHasChanges(true);
        };

    const toggleEdit = () => {
        if (isEditing && hasChanges) {
            // Save changes logic here
            setHasChanges(false);
        }
        setIsEditing(!isEditing);
    };

    return (
        <div className="max-w-6xl mx-auto p-6">
            {/* Header Section */}
            <div className="flex justify-between items-start mb-6">
                <div className="flex items-center gap-2">
                    <h1 className="text-[32px] font-bold text-gray-900 font-gilroy-bold">
                        Your Profile
                    </h1>
                </div>
                <button
                    onClick={toggleEdit}
                    className="flex items-center text-copper font-dmSans"
                >
                    {isEditing ? (
                        <>
                            <Save className="w-4 h-4 mr-1 text-copper" />
                            {hasChanges ? "Save Updates" : "Done"}
                        </>
                    ) : (
                        <>
                            <Pencil className="w-4 h-4 mr-1 text-copper" />
                            Edit
                        </>
                    )}
                </button>
            </div>

            <div className="px-4 space-y-4 mt-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1 font-dmSans">
                        Email address
                    </label>
                    <input
                        type="email"
                        value={email}
                        onChange={handleInputChange(setEmail)}
                        disabled={!isEditing}
                        className="w-full max-w-md px-3 py-2 border rounded-md disabled:bg-gray-50 disabled:text-gray-500"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1 font-dmSans">
                        Zip Code
                    </label>
                    <input
                        type="text"
                        value={zipCode}
                        onChange={handleInputChange(setZipCode)}
                        disabled={!isEditing}
                        className="w-full max-w-md px-3 py-2 border rounded-md disabled:bg-gray-50 disabled:text-gray-500"
                    />
                </div>
            </div>
        </div>
    );
};

export default UserDetailHeader;
