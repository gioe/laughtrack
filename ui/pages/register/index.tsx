import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

export default function LaughtrackSignup() {
    const url = new URL(
        `logo.png`,
        `https://${process.env.BUNNYCDN_CDN_HOST}/`,
    );
    const [showPassword, setShowPassword] = useState(false);

    return (
        <div className="flex min-h-screen bg-white">
            {/* Left Section - Signup Form */}
            <div className="w-1/2 p-8 flex flex-col">
                <div className="max-w-md mx-auto w-full">
                    <h1 className="text-2xl font-bold mb-2">Laughtrack</h1>
                    <h2 className="text-2xl font-bold mb-2">
                        Welcome to Laughtrack!
                    </h2>
                    <p className="text-gray-600 mb-6">
                        Fill in the fields to create your account.
                    </p>

                    <form className="space-y-4">
                        <div>
                            <label
                                htmlFor="email"
                                className="block text-sm font-medium mb-1"
                            >
                                Email
                            </label>
                            <input
                                type="email"
                                id="email"
                                placeholder="Enter your email..."
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brown-500"
                            />
                        </div>

                        <div>
                            <label
                                htmlFor="password"
                                className="block text-sm font-medium mb-1"
                            >
                                Password
                            </label>
                            <div className="relative">
                                <input
                                    type={showPassword ? "text" : "password"}
                                    id="password"
                                    placeholder="Enter your password..."
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brown-500 pr-10"
                                />
                                <button
                                    type="button"
                                    onClick={() =>
                                        setShowPassword(!showPassword)
                                    }
                                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500"
                                >
                                    {showPassword ? (
                                        <EyeOff size={20} />
                                    ) : (
                                        <Eye size={20} />
                                    )}
                                </button>
                            </div>
                        </div>

                        <div className="flex items-center">
                            <input
                                type="checkbox"
                                id="terms"
                                className="w-4 h-4 text-brown-600 border-gray-300 rounded focus:ring-brown-500"
                            />
                            <label
                                htmlFor="terms"
                                className="ml-2 text-sm text-gray-600"
                            >
                                I agree to the{" "}
                                <a
                                    href="#"
                                    className="text-brown-600 hover:underline"
                                >
                                    Terms and Conditions
                                </a>
                            </label>
                        </div>

                        <div className="space-y-4">
                            <div className="relative">
                                <div className="absolute inset-0 flex items-center">
                                    <div className="w-full border-t border-gray-300"></div>
                                </div>
                                <div className="relative flex justify-center text-sm">
                                    <span className="px-2 bg-white text-gray-500">
                                        or
                                    </span>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <button
                                    type="button"
                                    className="flex items-center justify-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                                >
                                    <img
                                        src="/api/placeholder/20/20"
                                        alt="Google"
                                        className="w-5 h-5 mr-2"
                                    />
                                    Sign Up with Google
                                </button>
                                <button
                                    type="button"
                                    className="flex items-center justify-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                                >
                                    <img
                                        src="/api/placeholder/20/20"
                                        alt="Apple"
                                        className="w-5 h-5 mr-2"
                                    />
                                    Sign Up with Apple
                                </button>
                            </div>

                            <button
                                type="submit"
                                className="w-full bg-brown-600 text-white py-2 rounded-lg hover:bg-brown-700 transition-colors"
                            >
                                Sign Up
                            </button>
                        </div>
                    </form>

                    <p className="mt-6 text-center text-sm text-gray-600">
                        Already have an account?{" "}
                        <a href="#" className="text-brown-600 hover:underline">
                            Sign In
                        </a>
                    </p>

                    <p className="mt-8 text-center text-sm text-gray-500">
                        Copyright © 2025 Laughtrack
                    </p>
                </div>
            </div>

            {/* Right Section - Image */}
            <div className="w-1/2 relative bg-gray-900">
                <img
                    src={url.toString()}
                    alt="Comedy show"
                    className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black bg-opacity-40 flex flex-col justify-end p-8 text-white">
                    <h2 className="text-3xl font-bold mb-4">Laugh Local</h2>
                    <p className="text-lg opacity-80">
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
