import React from "react";

const SocialButton = ({ provider, onClick, children }) => {
    const logos = {
        google: "/api/placeholder/20/20",
        apple: "/api/placeholder/20/20",
    };

    return (
        <button
            type="button"
            onClick={onClick}
            className="flex-1 flex items-center justify-center px-4 py-2 border border-gray-300 rounded-lg text-[12px] text-black bg-coconut-cream hover:bg-gray-50 font-dmSans"
        >
            <img
                src={logos[provider.toLowerCase()]}
                alt={`${provider} logo`}
                className="w-5 h-5 mr-2"
            />
            {children}
        </button>
    );
};

const SocialAuthButtons = ({
    onGoogleClick,
    onAppleClick,
    actionText = "Sign Up", // default text, can be "Log In" or "Sign Up"
}) => {
    return (
        <div className="flex gap-4">
            <SocialButton provider="google" onClick={onGoogleClick}>
                {actionText} with Google
            </SocialButton>
            <SocialButton provider="apple" onClick={onAppleClick}>
                {actionText} with Apple
            </SocialButton>
        </div>
    );
};

export default SocialAuthButtons;
