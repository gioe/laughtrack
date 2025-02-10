import { useSignOut } from "@/hooks/useSignOut";
import { FullRoundedButton } from "../../button/rounded/full";
import { HeaderItem } from "../../navbar/headerItem";
import { signOut } from "next-auth/react";

export default function AuthButtons({
    currentUser,
    pathname,
    onLogin,
    onSignup,
}) {
    const handleSignOut = useSignOut();

    return (
        <div className="flex items-center space-x-4">
            {currentUser ? (
                <div className="hidden lg:flex lg:gap-x-12 items-center">
                    <HeaderItem
                        highlighted={pathname.includes("/profile")}
                        href={`/profile/${currentUser.id}`}
                        title="Profile"
                    />
                    <FullRoundedButton
                        handleClick={handleSignOut}
                        label="Log Out"
                    />
                </div>
            ) : (
                <div className="hidden lg:flex lg:flex-1 lg:justify-end gap-3">
                    <FullRoundedButton handleClick={onLogin} label="Log In" />
                    <FullRoundedButton handleClick={onSignup} label="Sign Up" />
                </div>
            )}
        </div>
    );
}
