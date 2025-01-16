"use client";

import React from "react";
import { Copyright } from "@/ui/components/copyright";
import AuthImageContent from "@/ui/components/auth/image";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { registerSchema } from "@/ui/components/form/register/schema";
import { zodResolver } from "@hookform/resolvers/zod";
import RegistrationForm from "@/ui/components/form/register";

interface LaughtrackSignupProps {
    handleLoginPick: () => void;
    handleSubmit: () => void;
}

export default function LaughtrackSignup({
    handleLoginPick,
    handleSubmit,
}: LaughtrackSignupProps) {
    const form = useForm<z.infer<typeof registerSchema>>({
        resolver: zodResolver(registerSchema),
        defaultValues: {
            email: "",
            password: "",
            zipCode: "",
        },
    });

    const clickLoginButton = () => {
        handleLoginPick();
    };

    return (
        <div className="flex min-h-screen bg-coconut-cream">
            {/* Left Section - Login Form */}
            <div className="w-1/2 p-8 flex flex-col">
                <div className="w-full px-8 pt-8 mb-12">
                    <h1 className="text-3xl font-bold text-gray-900 font-chivo">
                        Laughtrack
                    </h1>
                </div>

                {/* Main Content */}
                <main className="flex-1 flex flex-col items-center px-4">
                    {/* Login Form */}
                    <div className="w-full max-w-md space-y-6">
                        <div className="text-center space-y-2">
                            <h2 className="text-2xl font-bold text-gray-900 font-inter text-[28px]">
                                Welcome
                            </h2>
                            <p className="text-gray-600 font-dmSans text-[16px]">
                                Fill in the fields to create your account.
                            </p>
                        </div>
                        <RegistrationForm onSubmit={handleSubmit} />

                        {/* Sign Up Link */}
                        <p className="text-center text-gray-600 font-dmSans text-[16px] pt-10">
                            Already have an account?{" "}
                            <a
                                className="text-brown-600 hover:text-brown-500 hover:cursor-pointer"
                                onClick={clickLoginButton}
                            >
                                Log In
                            </a>
                        </p>
                    </div>
                </main>

                <Copyright />
            </div>

            {/* Right Section - Image */}
            <AuthImageContent />
        </div>
    );
}
