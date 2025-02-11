import React from "react";
import GoogleGLogo from "../../icons/GoogleIcon";
import AppleLogo from "../../icons/AppleIcon";
import { signIn } from "@/auth";

const SocialButton = ({ provider, onClick, children }) => {
    const logos = {
        google: <GoogleGLogo />,
        apple: <AppleLogo />,
    };

    return (
        <button
            type="button"
            onClick={onClick}
            className="flex-1 flex items-center justify-center px-4 py-2 border border-gray-300 rounded-lg text-[12px] text-black bg-coconut-cream hover:bg-gray-50 font-dmSans"
        >
            <div className="pr-2">{logos[provider.toLowerCase()]}</div>
            {children}
        </button>
    );
};

const SocialAuthButtons = ({
    actionText = "Sign up", // default text, can be "Log In" or "Sign Up"
}) => {
    return (
        <div className="flex gap-4">
            <SocialButton
                provider="google"
                onClick={async () => {
                    "use server";
                    await signIn("google");
                }}
            >
                {actionText} with Google
            </SocialButton>
            <SocialButton
                provider="apple"
                onClick={async () => {
                    "use server";
                    await signIn("apple");
                }}
            >
                {actionText} with Apple
            </SocialButton>
        </div>
    );
};

export default SocialAuthButtons;
