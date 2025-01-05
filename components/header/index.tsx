"use client";
import { Popover, PopoverButton, PopoverGroup } from "@headlessui/react";
import useLoginModal from "../../hooks/modalState/useLoginModal";
import useRegisterModal from "../../hooks/modalState/useRegisterModel";
import { useCallback } from "react";
import { HeaderItem } from "../navbar/headerItem";
import { ChevronDownIcon } from "@heroicons/react/24/solid";
import { FullRoundedButton } from "../button/rounded/full";
import { signOut } from "next-auth/react";
import { UserInterface } from "../../objects/interface";
import { HamburgerMenuButton } from "../button/hamburger";
import {
    FaceSmileIcon,
    BuildingStorefrontIcon,
} from "@heroicons/react/24/outline";
import NavbarPopoverItem from "../popover/panel";

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
    onClick: (open: boolean) => void;
    currentUser?: UserInterface | null;
}

export function Header({ onClick, currentUser }: HeaderProps) {
    const loginModal = useLoginModal();
    const registerModal = useRegisterModal();
    const handleLoginClick = useCallback(() => {
        loginModal.onOpen();
    }, [loginModal]);

    const handleSignupClick = useCallback(() => {
        registerModal.onOpen();
    }, [registerModal]);

    return (
        <header className="bg-ivory">
            <nav
                aria-label="Global"
                className="mx-auto flex max-w-7xl items-center justify-between p-6 lg:px-8"
            >
                <div className="flex lg:hidden">
                    <HamburgerMenuButton handleClick={() => onClick(true)} />
                </div>
                <div className="hidden lg:flex lg:gap-x-12">
                    <HeaderItem href="/" title="Home" />
                    <PopoverGroup className="hidden lg:flex lg:gap-x-12">
                        <Popover className="relative">
                            <PopoverButton className="flex items-center gap-x-1 leading-6">
                                <HeaderItem title="Clubs" />
                                <ChevronDownIcon
                                    aria-hidden="true"
                                    className="h-5 w-5 flex-none text-soft-charcoal"
                                />
                            </PopoverButton>

                            <NavbarPopoverItem items={clubMenuItems} />
                        </Popover>

                        <Popover className="relative">
                            <PopoverButton className="flex items-center gap-x-1 leading-6">
                                <HeaderItem title="Comedians" />
                                <ChevronDownIcon
                                    aria-hidden="true"
                                    className="h-5 w-5 flex-none text-soft-charcoal"
                                />
                            </PopoverButton>

                            <NavbarPopoverItem items={comedianMenuItems} />
                        </Popover>
                    </PopoverGroup>
                </div>

                <div className="hidden lg:flex lg:flex-1 lg:justify-end">
                    {currentUser ? (
                        <div className="hidden lg:flex lg:gap-x-12 items-center">
                            <HeaderItem
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
        </header>
    );
}
