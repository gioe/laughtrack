"use client";
import { useCallback } from "react";
import { usePathname } from "next/navigation";
import { useLoginModal } from "@/hooks/modal";
import Logo from "../logo";
import NavigationMenu from "../navbar/menu";
import AuthButtons from "../auth/header";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { useStyleContext } from "@/contexts/StyleProvider";

interface HeaderProps {
    currentUser?: UserProfileInterface | null;
}

export function Header({ currentUser }: HeaderProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const pathname = usePathname();

    const loginModal = useLoginModal();

    const handleLoginClick = useCallback(() => {
        loginModal.onOpen();
    }, [loginModal]);

    return (
        <nav
            className={`relative px-4 py-4 ${styleConfig.headerBackgroundColor}`}
        >
            <div className="hidden max-w-7xl mx-auto items-center lg:grid lg:grid-cols-3 ">
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
                    />
                </div>
            </div>
        </nav>
    );
}
