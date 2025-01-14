"use client";
import { useCallback } from "react";
import { usePathname } from "next/navigation";
import { useLoginModal, useRegisterModal } from "@/hooks/modalState";
import { UserInterface } from "@/objects/class/user/user.interface";
import Logo from "../logo";
import NavigationMenu from "../navbar/menu";
import AuthButtons from "../auth";

interface HeaderProps {
    currentUser?: UserInterface | null;
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
            <div className="max-w-7xl mx-auto grid grid-cols-3 items-center">
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
