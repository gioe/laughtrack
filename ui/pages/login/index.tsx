"use client";
import React, { useState } from "react";
import SocialAuthButtons from "@/ui/components/auth/social";
import PasswordInput from "@/ui/components/input/password";
import EmailInput from "@/ui/components/input/email";
import FormSubmissionButton from "@/ui/components/button/form";

interface LaughtrackLoginProps {
    handleRegisterClick: () => void;
}
function LaughtrackLogin({ handleRegisterClick }: LaughtrackLoginProps) {
    const url = new URL(`sidebar.png`, `https:/laughtrack.b-cdn.net/`);
    const [showPassword, setShowPassword] = useState(false);

    const clickRegisterButton = () => {
        handleRegisterClick();
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
                                Welcome back
                            </h2>
                            <p className="text-gray-600 font-dmSans text-[16px]">
                                Please log in to access your account.
                            </p>
                        </div>

                        <form className="space-y-6">
                            {/* Email Input */}
                            <EmailInput
                                value={""}
                                onChange={(e) => {}}
                                label="Email"
                                placeholder="Enter your email..."
                            />

                            {/* Password Input */}
                            <PasswordInput
                                value={"password"}
                                onChange={(e) => {}}
                                label="Password"
                                placeholder="Enter your password..."
                            />

                            {/* Remember Me and Forgot Password */}
                            <div className="flex items-center justify-between">
                                <a
                                    href="#"
                                    className="text-sm text-brown-600 hover:text-brown-500"
                                >
                                    Forgot password?
                                </a>
                            </div>

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

                            <FormSubmissionButton>Log In</FormSubmissionButton>
                        </form>

                        {/* Sign Up Link */}
                        <p className="text-center text-gray-600 font-dmSans text-[16px]">
                            Don't have an account yet?{" "}
                            <a
                                className="text-brown-600 hover:text-brown-500 pt-20 hover:cursor-pointer"
                                onClick={clickRegisterButton}
                            >
                                Sign Up
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

export default LaughtrackLogin;
