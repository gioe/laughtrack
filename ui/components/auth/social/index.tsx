import React from "react";
import GoogleGLogo from "../../icons/GoogleIcon";
import AppleLogo from "../../icons/AppleIcon";

const SocialButton = ({ provider, onClick, children }) => {
    const logos = {
        google: <GoogleGLogo />,
        apple: <AppleLogo />,
    };

    return (
        <button
            type="button"
            onClick={onClick}
            className="flex-1 flex items-center justify-center px-4 py-2 border
             border-gray-300 rounded-lg text-[12px] text-black font-dmSans
              bg-coconut-cream hover:bg-copper "
        >
            <div className="pr-2">{logos[provider.toLowerCase()]}</div>
            {children}
        </button>
    );
};

const SocialAuthButtons = ({
    actionText = "Continue",
    handleGoogleSignin,
    handleAppleSignin,
}) => {
    return (
        <div className="flex flex-col gap-4">
            <SocialButton provider="google" onClick={handleGoogleSignin}>
                {actionText} with Google
            </SocialButton>
            {/* <SocialButton provider="apple" onClick={handleAppleSignin}>
                {actionText} with Apple
            </SocialButton> */}
        </div>
    );
};

export default SocialAuthButtons;
