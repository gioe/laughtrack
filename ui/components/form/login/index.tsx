/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import SocialAuthButtons from "../../auth/social";
import toast from "react-hot-toast";
import { signIn } from "next-auth/react";
import { motion } from "framer-motion";

interface LoginFormProps {
    onSubmit: () => void;
}

export default function LoginForm({ onSubmit }: LoginFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const googleSignIn = async () => {
        try {
            setIsLoading(true);
            await signIn("google");
        } catch (error) {
            toast.error("Failed to sign in with Google");
            setIsLoading(false);
        }
    };

    const appleSignIn = async () => {
        try {
            setIsLoading(true);
            await signIn("apple");
        } catch (error) {
            toast.error("Failed to sign in with Apple");
            setIsLoading(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="relative"
        >
            <div className="space-y-6">
                <SocialAuthButtons
                    handleAppleSignin={appleSignIn}
                    handleGoogleSignin={googleSignIn}
                />
            </div>
            {isLoading && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur-sm rounded-lg"
                >
                    <div className="flex flex-col items-center gap-2">
                        <Loader2 className="w-8 h-8 text-[#8B593B] animate-spin" />
                        <p className="text-sm text-gray-600 font-dmSans">
                            Connecting to your account...
                        </p>
                    </div>
                </motion.div>
            )}
        </motion.div>
    );
}
