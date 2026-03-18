"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { makeRequest } from "@/util/actions/makeRequest";
import { APIRoutePath, RestAPIAction } from "@/objects/enum";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";

interface EditableFieldsState {
    emailOptin: boolean;
    zipCode: string;
}

export function useProfileForm(profile: UserProfileInterface) {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const [fields, setFields] = useState<EditableFieldsState>({
        emailOptin: profile.emailOptin ?? false,
        zipCode: profile.zipCode ?? "",
    });
    const [dirtyFields, setDirtyFields] = useState<
        Partial<EditableFieldsState>
    >({});

    useEffect(() => {
        setFields({
            emailOptin: profile.emailOptin ?? false,
            zipCode: profile.zipCode ?? "",
        });
        setDirtyFields({});
    }, [profile]);

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

            setDirtyFields({});
            toast.success("Updated successfully");
            router.refresh();
        } catch (error) {
            console.error("Failed to update profile:", error);
            toast.error("Something went wrong");
            setFields({
                emailOptin: profile.emailOptin ?? false,
                zipCode: profile.zipCode ?? "",
            });
            setDirtyFields({});
        } finally {
            setIsLoading(false);
        }
    };

    return { fields, dirtyFields, isLoading, handleFieldChange, handleSave };
}
