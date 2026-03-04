"use client";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import SocialAuthButtons from "../../auth/social";
import toast from "react-hot-toast";
import { signIn } from "next-auth/react";
import { motion } from "framer-motion";
import { Form } from "../../ui/form";
import { FormInput } from "../components/input";

const loginSchema = z.object({
    email: z.string().email("Please enter a valid email address"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

interface LoginFormProps {
    onSubmit: () => void;
}

export default function LoginForm({ onSubmit }: LoginFormProps) {
    const [isSocialLoading, setIsSocialLoading] = useState(false);

    const form = useForm<LoginFormValues>({
        resolver: zodResolver(loginSchema),
        defaultValues: { email: "" },
        mode: "onBlur",
    });

    const isSubmitting = form.formState.isSubmitting;
    const isLoading = isSocialLoading || isSubmitting;

    const handleEmailSubmit = async (values: LoginFormValues) => {
        try {
            const result = await signIn("email", {
                email: values.email,
                redirect: false,
            });
            if (result?.error) {
                toast.error("Failed to send sign-in link. Please try again.");
            } else {
                toast.success("Check your email for a sign-in link!");
                onSubmit();
            }
        } catch {
            toast.error("Something went wrong. Please try again.");
        }
    };

    const googleSignIn = async () => {
        try {
            setIsSocialLoading(true);
            await signIn("google");
        } catch {
            toast.error("Failed to sign in with Google");
        } finally {
            setIsSocialLoading(false);
        }
    };

    const appleSignIn = async () => {
        try {
            setIsSocialLoading(true);
            await signIn("apple");
        } catch {
            toast.error("Failed to sign in with Apple");
        } finally {
            setIsSocialLoading(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="relative space-y-6"
        >
            <SocialAuthButtons
                handleAppleSignin={appleSignIn}
                handleGoogleSignin={googleSignIn}
            />

            <div className="relative flex items-center gap-3">
                <div className="flex-1 border-t border-gray-200" />
                <span className="text-sm text-gray-400 font-dmSans">or</span>
                <div className="flex-1 border-t border-gray-200" />
            </div>

            <Form {...form}>
                <form
                    onSubmit={form.handleSubmit(handleEmailSubmit)}
                    noValidate
                >
                    <div className="space-y-4">
                        <FormInput
                            isLoading={isLoading}
                            form={form}
                            name="email"
                            label="Email"
                            placeholder="you@example.com"
                            type="email"
                        />
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full flex items-center justify-center gap-2 px-6 py-3
                                border border-[#8B593B] rounded-xl text-[14px] text-white font-dmSans
                                bg-[#8B593B] hover:bg-[#7a4e33] transition-colors duration-200
                                shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2
                                focus:ring-[#8B593B] disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    <span>
                                        {isSubmitting
                                            ? "Sending link…"
                                            : "Loading…"}
                                    </span>
                                </>
                            ) : (
                                "Continue with Email"
                            )}
                        </button>
                    </div>
                </form>
            </Form>

            {isSocialLoading && (
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
