/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import SocialAuthButtons from "../../auth/social";

interface LoginFormProps {
    onSubmit: () => void;
}

export default function LoginForm() {
    const [isLoading, setIsLoading] = useState(false);

    return (
        <div>
            <div className="space-y-6">
                <SocialAuthButtons />
            </div>
            {isLoading && (
                <div className="z-10 absolute inset-0 flex items-center justify-center bg-white/50 rounded-lg">
                    <Loader2 className="w-8 h-8 text-[#8B593B] animate-spin" />
                </div>
            )}
        </div>
    );
}
