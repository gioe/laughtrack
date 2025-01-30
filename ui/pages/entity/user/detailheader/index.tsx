"use client";

import React, { useState } from "react";
import { Pencil, Save } from "lucide-react";
import { makeRequest } from "@/util/actions/makeRequest";
import { APIRoutePath, RestAPIAction } from "@/objects/enum";

interface UserDetailHeaderProps {
    userProfile: UserProfileResponse;
}
const UserDetailHeader = ({ userProfile }: UserDetailHeaderProps) => {
    const [isEditing, setIsEditing] = useState(false);
    const [email, setEmail] = useState(userProfile.email);
    const [emailOptin, setEmailOptin] = useState(userProfile.emailOptin);
    const [zipCode, setZipCode] = useState(userProfile.zipcode);
    const [hasChanges, setHasChanges] = useState(false);

    const checkForChanges = () => {
        return (
            email !== userProfile.email ||
            zipCode !== userProfile.zipcode ||
            emailOptin !== userProfile.emailOptin
        );
    };

    const handleInputChange =
        (setter: (arg0: any) => void, isCheckbox: boolean = false) =>
        (e: { target: { value: any; checked: boolean } }) => {
            const newValue = isCheckbox ? e.target.checked : e.target.value;
            setter(newValue);
            console.log(email !== userProfile.email);
            console.log(zipCode !== userProfile.zipcode);
            console.log(emailOptin !== userProfile.emailOptin);

            setHasChanges(checkForChanges());
        };

    const toggleEdit = async () => {
        if (isEditing && hasChanges) {
            try {
                const response = await makeRequest(APIRoutePath.Profile, {
                    method: RestAPIAction.PUT,
                    body: {
                        email: email,
                        zipCode: zipCode,
                        emailOptin: emailOptin,
                    },
                });

                // If the request is successful, update the original user data
                userProfile.email = email;
                userProfile.zipcode = zipCode;

                setHasChanges(false);
            } catch (error) {
                // Handle error appropriately
                console.error("Failed to update profile:", error);
                // Optionally reset form to original values
                setEmail(userProfile.email);
                setZipCode(userProfile.zipcode);
                // You might want to show an error message to the user here
                return; // Don't toggle edit mode if save failed
            }
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
                <div className="flex items-center space-x-2">
                    <input
                        checked={emailOptin}
                        type="checkbox"
                        id="emailOptIn"
                        className="h-4 w-4 rounded border-gray-300 text-brown-600 focus:ring-brown-500"
                        onChange={handleInputChange(setEmailOptin, true)}
                        disabled={!isEditing}
                    />
                    <label
                        htmlFor="emailOptIn"
                        className="text-sm text-gray-600"
                    >
                        Email me when artists I follow have shows in my area
                    </label>
                </div>
            </div>
        </div>
    );
};

export default UserDetailHeader;
