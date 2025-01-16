"use client";

import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import SocialAuthButtons from "@/ui/components/auth/social";
import PasswordInput from "@/ui/components/input/password";
import EmailInput from "@/ui/components/input/email";
import ZipCodeInput from "@/ui/components/input/zipcode/input";
import FormSubmissionButton from "@/ui/components/button/form";

interface LaughtrackSignupProps {
    handleLoginPick: () => void;
}

export default function LaughtrackSignup({
    handleLoginPick,
}: LaughtrackSignupProps) {
    const url = new URL(`sidebar.png`, `https:/laughtrack.b-cdn.net/`);
    const [showPassword, setShowPassword] = useState(false);

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

                        <form className="space-y-6">
                            <EmailInput
                                value={""}
                                onChange={(e) => {}}
                                label="Email"
                                placeholder="Enter your email..."
                            />
                            <PasswordInput
                                value={""}
                                onChange={(e) => {}}
                                label="Password"
                                placeholder="Enter your password..."
                            />
                            <ZipCodeInput
                                value={""}
                                onChange={(e) => {}}
                                label="Zip Code"
                                placeholder="Enter your zip code..."
                            />

                            {/* Divider */}
                            <div className="relative">
                                <div className="absolute inset-0 flex items-center">
                                    <div className="w-full border-t border-gray-300"></div>
                                </div>
                                <div className="relative flex justify-center text-sm">
                                    <span className="px-2 bg-cream-50 text-gray-500">
                                        or
                                    </span>
                                </div>
                            </div>

                            {/* Social Login Buttons */}
                            <SocialAuthButtons
                                onAppleClick={() => {}}
                                onGoogleClick={() => {}}
                            />

                            {/* Login Button */}
                            <FormSubmissionButton>Sign Up</FormSubmissionButton>
                        </form>

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

                {/* Footer */}
                <footer className="px-8 py-4 text-gray-500 text-[16px] font-dmSans">
                    Copyright © 2025 Laughtrack
                </footer>
            </div>

            {/* Right Section - Image */}
            <div className="w-1/2 relative bg-gray-900">
                <img
                    src={url.toString()}
                    alt="Comedy show"
                    className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black bg-opacity-40 flex flex-col justify-end p-8 text-white text-center font-inter text-[28px]">
                    <h2 className="text-3xl font-bold mb-4">Laugh Local</h2>

                    <p className="text-[14px] opacity-80 font-dmSans">
                        Laughtrack wants to get you out of the house. Find funny
                        shows. Follow funny comedians. Get informed when funny
                        comedians put on funny shows. Turn off that podcast and
                        go see the real thing.
                    </p>
                </div>
            </div>
        </div>
    );
}
