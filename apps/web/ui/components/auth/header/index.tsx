import { useSignOut } from "@/hooks/useSignOut";
import { Button } from "../../ui/button";
import { HeaderItem } from "../../navbar/headerItem";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";

interface AuthButtonsProps {
    currentUser: UserProfileInterface | null | undefined;
    pathname: string;
    onLogin: () => void;
}

export default function AuthButtons({
    currentUser,
    pathname,
    onLogin,
}: AuthButtonsProps) {
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
                    <Button
                        type="button"
                        variant="roundedShimmer"
                        onClick={handleSignOut}
                    >
                        Log Out
                    </Button>
                </div>
            ) : (
                <div className="hidden lg:flex lg:flex-1 lg:justify-end gap-3">
                    <Button
                        type="button"
                        variant="roundedShimmer"
                        onClick={onLogin}
                    >
                        Log In
                    </Button>
                </div>
            )}
        </div>
    );
}
