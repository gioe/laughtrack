"use client";
import { useCallback } from "react";
import { usePathname } from "next/navigation";
import { useLoginModal, useRegisterModal } from "@/hooks/modalState";
import Logo from "../logo";
import NavigationMenu from "../navbar/menu";
import AuthButtons from "../auth/header";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";

interface HeaderProps {
    currentUser?: UserProfileInterface | null;
}

export function Header({ currentUser }: HeaderProps) {
    const pathname = usePathname();

    const loginModal = useLoginModal();
    const registerModal = useRegisterModal();

    const handleLoginClick = useCallback(() => {
        loginModal.onOpen();
    }, [loginModal]);

    const handleSignupClick = useCallback(() => {
        registerModal.onOpen();
    }, [registerModal]);

    return (
        <nav className="relative bg-transparent px-4 py-4">
            <div className="hidden lg:grid max-w-7xl mx-auto lg:grid-cols-3 items-center">
                {/* Left column - Logo */}
                <div className="col-start-1">
                    <Logo />
                </div>
                <div className="col-start-2 justify-self-center">
                    <NavigationMenu pathname={pathname} />
                </div>
                <div className="col-start-3 justify-self-end">
                    <AuthButtons
                        currentUser={currentUser}
                        pathname={pathname}
                        onLogin={handleLoginClick}
                        onSignup={handleSignupClick}
                    />
                </div>
            </div>
        </nav>
    );
}
