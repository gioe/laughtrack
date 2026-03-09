import React from "react";
import GoogleGLogo from "../../icons/GoogleIcon";
import AppleLogo from "../../icons/AppleIcon";
import { motion, useReducedMotion } from "framer-motion";

interface SocialButtonProps {
    provider: "google" | "apple";
    onClick: () => void;
    children: React.ReactNode;
}

const SocialButton = ({ provider, onClick, children }: SocialButtonProps) => {
    const prefersReducedMotion = useReducedMotion();

    const logos = {
        google: <GoogleGLogo />,
        apple: <AppleLogo />,
    };

    return (
        <motion.button
            type="button"
            onClick={onClick}
            whileHover={prefersReducedMotion ? undefined : { scale: 1.02 }}
            whileTap={prefersReducedMotion ? undefined : { scale: 0.98 }}
            className="w-full flex items-center justify-center gap-3 px-6 py-3
                border border-gray-200 rounded-xl text-[14px] text-gray-700 font-dmSans
                bg-white hover:bg-gray-50 transition-colors duration-200
                shadow-sm hover:shadow focus:outline-none focus:ring-2
                focus:ring-offset-2 focus:ring-[#8B593B]"
        >
            <div className="flex items-center justify-center w-5 h-5">
                {logos[provider]}
            </div>
            <span className="font-medium">{children}</span>
        </motion.button>
    );
};

interface SocialAuthButtonsProps {
    actionText?: string;
    handleGoogleSignin: () => void;
    handleAppleSignin: () => void;
}

const SocialAuthButtons = ({
    actionText = "Continue",
    handleGoogleSignin,
}: SocialAuthButtonsProps) => {
    const prefersReducedMotion = useReducedMotion();

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: prefersReducedMotion
                ? { duration: 0 }
                : { staggerChildren: 0.1 },
        },
    };

    const item = {
        hidden: { opacity: 0, y: prefersReducedMotion ? 0 : 20 },
        show: { opacity: 1, y: 0 },
    };

    return (
        <motion.div
            className="flex flex-col gap-4"
            variants={container}
            initial="hidden"
            animate="show"
        >
            <motion.div variants={item}>
                <SocialButton provider="google" onClick={handleGoogleSignin}>
                    {actionText} with Google
                </SocialButton>
            </motion.div>
            {/* Uncomment when Apple sign-in is ready */}
            {/* <motion.div variants={item}>
                <SocialButton provider="apple" onClick={handleAppleSignin}>
                    {actionText} with Apple
                </SocialButton>
            </motion.div> */}
        </motion.div>
    );
};

export default SocialAuthButtons;
