"use client";

import { useCallback, useState } from "react";
import { signOut } from "next-auth/react";
import {
    Popover,
    PopoverButton,
    PopoverGroup,
    PopoverPanel,
} from "@headlessui/react";
import {
    FaceSmileIcon,
    BuildingStorefrontIcon,
} from "@heroicons/react/24/outline";
import { ChevronDownIcon } from "@heroicons/react/24/solid";
import useLoginModal from "../../hooks/modalState/useLoginModal";
import useRegisterModal from "../../hooks/modalState/useRegisterModel";
import { UserInterface } from "../../objects/interface";
import { HamburgerMenuButton } from "../button/hamburger";
import { HeaderItem } from "./headerItem";
import { RoundedButton } from "../button/rounded";
import { SideDrawer } from "../sidedrawer";

const comedianMenuItems = [
    {
        name: "Search",
        description: "Search for your favorite comedians",
        href: "/comedian/all",
        icon: FaceSmileIcon,
    },
];

const clubMenuItems = [
    {
        name: "Search",
        description: "Search for clubs in your area",
        href: "/club/all",
        icon: BuildingStorefrontIcon,
    },
];

interface NavbarProps {
    currentUser?: UserInterface | null;
}

const Header: React.FC<NavbarProps> = ({ currentUser }) => {
    const loginModal = useLoginModal();
    const registerModal = useRegisterModal();

    const handleLoginClick = useCallback(() => {
        loginModal.onOpen();
    }, [loginModal]);

    const handleSignupClick = useCallback(() => {
        registerModal.onOpen();
    }, [registerModal]);

    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    return (
        <header className="bg-ivory">
            <nav
                aria-label="Global"
                className="mx-auto flex max-w-7xl items-center justify-between p-6 lg:px-8"
            >
                <div className="flex lg:hidden">
                    <HamburgerMenuButton
                        handleClick={() => setMobileMenuOpen(true)}
                    ></HamburgerMenuButton>
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

                            <PopoverPanel
                                transition
                                className="absolute -left-8 top-full z-10 mt-3 w-screen max-w-md overflow-hidden rounded-3xl bg-white shadow-lg ring-1 ring-gray-900/5 transition data-[closed]:translate-y-1 data-[closed]:opacity-0 data-[enter]:duration-200 data-[leave]:duration-150 data-[enter]:ease-out data-[leave]:ease-in"
                            >
                                <div className="p-4">
                                    {clubMenuItems.map((item) => (
                                        <div
                                            key={item.name}
                                            className="group relative flex items-center gap-x-6 rounded-lg p-4 text-sm leading-6 hover:bg-gray-50"
                                        >
                                            <div className="flex h-11 w-11 flex-none items-center justify-center rounded-lg bg-gray-50 group-hover:bg-white">
                                                <item.icon
                                                    aria-hidden="true"
                                                    className="h-6 w-6 text-gray-600 group-hover:text-indigo-600"
                                                />
                                            </div>
                                            <div className="flex-auto">
                                                <a
                                                    href={item.href}
                                                    className="block font-semibold text-gray-900"
                                                >
                                                    {item.name}
                                                    <span className="absolute inset-0" />
                                                </a>
                                                <p className="mt-1 text-gray-600">
                                                    {item.description}
                                                </p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </PopoverPanel>
                        </Popover>

                        <Popover className="relative">
                            <PopoverButton className="flex items-center gap-x-1 leading-6">
                                <HeaderItem title="Comedians" />
                                <ChevronDownIcon
                                    aria-hidden="true"
                                    className="h-5 w-5 flex-none text-soft-charcoal"
                                />
                            </PopoverButton>

                            <PopoverPanel
                                transition
                                className="absolute -left-8 top-full z-10 mt-3 w-screen max-w-md overflow-hidden rounded-3xl bg-white shadow-lg ring-1 ring-gray-900/5 transition data-[closed]:translate-y-1 data-[closed]:opacity-0 data-[enter]:duration-200 data-[leave]:duration-150 data-[enter]:ease-out data-[leave]:ease-in"
                            >
                                <div className="p-4">
                                    {comedianMenuItems.map((item) => (
                                        <div
                                            key={item.name}
                                            className="group relative flex items-center gap-x-6 rounded-lg p-4 text-sm leading-6 hover:bg-gray-50"
                                        >
                                            <div className="flex h-11 w-11 flex-none items-center justify-center rounded-lg bg-gray-50 group-hover:bg-white">
                                                <item.icon
                                                    aria-hidden="true"
                                                    className="h-6 w-6 text-gray-600 group-hover:text-indigo-600"
                                                />
                                            </div>
                                            <div className="flex-auto">
                                                <a
                                                    href={item.href}
                                                    className="block font-semibold text-gray-900"
                                                >
                                                    {item.name}
                                                    <span className="absolute inset-0" />
                                                </a>
                                                <p className="mt-1 text-gray-600">
                                                    {item.description}
                                                </p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </PopoverPanel>
                        </Popover>
                    </PopoverGroup>
                    {currentUser && (
                        <HeaderItem
                            href={`/profile/${currentUser.id}`}
                            title="Profile"
                        />
                    )}
                </div>

                <div className="hidden lg:flex lg:flex-1 lg:justify-end">
                    {currentUser ? (
                        <RoundedButton handleClick={signOut} title="Log Out" />
                    ) : (
                        <div className="hidden lg:flex lg:flex-1 lg:justify-end gap-3">
                            <RoundedButton
                                handleClick={handleLoginClick}
                                title="Log In"
                            />
                            <RoundedButton
                                handleClick={handleSignupClick}
                                title="Sign Up"
                            />
                        </div>
                    )}
                </div>
            </nav>
            <div className="lg:hidden">
                <SideDrawer
                    open={mobileMenuOpen}
                    onClose={setMobileMenuOpen}
                    currentUser={currentUser}
                />
            </div>
        </header>
    );
};

export default Header;
