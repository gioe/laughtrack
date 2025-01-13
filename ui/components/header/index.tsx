"use client";
import { Popover, PopoverButton, PopoverGroup } from "@headlessui/react";
import { useCallback } from "react";
import { ChevronDownIcon } from "@heroicons/react/24/solid";
import { FullRoundedButton } from "../button/rounded/full";
import { signOut } from "next-auth/react";
import {
    FaceSmileIcon,
    BuildingStorefrontIcon,
} from "@heroicons/react/24/outline";
import NavbarPopoverItem from "../popover/panel";
import { usePathname } from "next/navigation";
import { useLoginModal, useRegisterModal } from "@/hooks/modalState";
import { UserInterface } from "@/objects/class/user/user.interface";
import { HeaderItem } from "../navbar/headerItem";
import { styleContexts } from "./styles";
import { useStyleContext } from "@/contexts/StyleProvider";

const comedianMenuItems = [
    {
        name: "Search",
        description: "Search for comedians you're interested in",
        href: "/comedian/all",
        icon: FaceSmileIcon,
    },
];

const clubMenuItems = [
    {
        name: "Search",
        description: "Search for clubs you're interested in",
        href: "/club/all",
        icon: BuildingStorefrontIcon,
    },
];

interface HeaderProps {
    currentUser?: UserInterface | null;
    styleContext?: keyof typeof styleContexts;
}

export function Header({ currentUser }: HeaderProps) {
    const pathname = usePathname();

    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const loginModal = useLoginModal();
    const registerModal = useRegisterModal();

    const handleLoginClick = useCallback(() => {
        loginModal.onOpen();
    }, [loginModal]);

    const handleSignupClick = useCallback(() => {
        registerModal.onOpen();
    }, [registerModal]);

    return (
        <nav className="bg-transparent px-4 py-4 flex items-center justify-between">
            {/* Logo/Brand */}
            <div className="flex items-center">
                <span
                    className={`${styleConfig.logoTextColor} text-2xl font-bold`}
                >
                    Laughtrack
                </span>
            </div>

            {/* Navigation Links */}
            <div className="flex items-center space-x-8">
                <HeaderItem
                    highlighted={pathname == "/"}
                    href="/"
                    title="Home"
                />
                <div className="flex items-center space-x-8"></div>

                {/* Clubs Dropdown */}
                <PopoverGroup className="flex lg;items-center space-x-8">
                    <Popover className="relative">
                        <PopoverButton className="flex items-center gap-x-1 leading-6">
                            <HeaderItem
                                highlighted={pathname.includes("/club")}
                                title="Clubs"
                            />
                            <ChevronDownIcon
                                aria-hidden="true"
                                className="h-5 w-5 flex-none text-soft-charcoal"
                            />
                        </PopoverButton>

                        <NavbarPopoverItem items={clubMenuItems} />
                    </Popover>

                    <Popover className="relative">
                        <PopoverButton className="flex items-center gap-x-1 leading-6">
                            <HeaderItem
                                highlighted={pathname.includes("/comedian")}
                                title="Comedians"
                            />
                            <ChevronDownIcon
                                aria-hidden="true"
                                className="h-5 w-5 flex-none text-soft-charcoal"
                            />
                        </PopoverButton>

                        <NavbarPopoverItem items={comedianMenuItems} />
                    </Popover>
                </PopoverGroup>
            </div>

            {/* Log Out Button */}
            <div className="flex items-center space-x-4">
                {currentUser ? (
                    <div className="hidden lg:flex lg:gap-x-12 items-center">
                        <HeaderItem
                            highlighted={pathname.includes("/profile")}
                            href={`profile/${currentUser.id}`}
                            title="Profile"
                        />
                        <FullRoundedButton
                            handleClick={signOut}
                            label="Log Out"
                        />
                    </div>
                ) : (
                    <div className="hidden lg:flex lg:flex-1 lg:justify-end gap-3">
                        <FullRoundedButton
                            handleClick={handleLoginClick}
                            label="Log In"
                        />
                        <FullRoundedButton
                            handleClick={handleSignupClick}
                            label="Sign Up"
                        />
                    </div>
                )}
            </div>
        </nav>
    );
}
