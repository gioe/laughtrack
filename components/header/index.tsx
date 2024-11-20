"use client";

import { useCallback, useState } from "react";
import { signOut } from "next-auth/react";
import {
    Dialog,
    DialogPanel,
    Disclosure,
    DisclosureButton,
    Popover,
    PopoverButton,
    PopoverGroup,
    PopoverPanel,
} from "@headlessui/react";
import {
    Bars3Icon,
    FaceSmileIcon,
    XMarkIcon,
    BuildingStorefrontIcon,
} from "@heroicons/react/24/outline";
import { ChevronDownIcon } from "@heroicons/react/24/solid";
import useLoginModal from "../../hooks/modalState/useLoginModal";
import useRegisterModal from "../../hooks/modalState/useRegisterModel";
import { UserInterface } from "../../objects/interface";
import { useScrapeMenuModal } from "../../hooks/modalState";

const comedianMenuItems = [
    {
        name: "Browse",
        description: "Search for your favorite comedians",
        href: "/comedian/all",
        icon: FaceSmileIcon,
    },
];

const clubMenuItems = [
    {
        name: "Browse",
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
    const scrapeMenuModal = useScrapeMenuModal();

    const handleLoginClick = useCallback(() => {
        loginModal.onOpen();
    }, [loginModal]);

    const handleSignupClick = useCallback(() => {
        registerModal.onOpen();
    }, [registerModal]);

    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    return (
        <header className="bg-white">
            <nav
                aria-label="Global"
                className="mx-auto flex max-w-7xl items-center justify-between p-6 lg:px-8"
            >
                <div className="flex lg:hidden">
                    <button
                        type="button"
                        onClick={() => setMobileMenuOpen(true)}
                        className="-m-2.5 inline-flex items-center justify-center rounded-md p-2.5 text-gray-700"
                    >
                        <span className="sr-only">Open main menu</span>
                        <Bars3Icon aria-hidden="true" className="h-6 w-6" />
                    </button>
                </div>
                <PopoverGroup className="hidden lg:flex lg:gap-x-12">
                    <a
                        href="/"
                        className="text-sm font-semibold leading-6 text-gray-900"
                    >
                        Home
                    </a>

                    <Popover className="relative">
                        <PopoverButton className="flex items-center gap-x-1 text-sm font-semibold leading-6 text-gray-900">
                            Clubs
                            <ChevronDownIcon
                                aria-hidden="true"
                                className="h-5 w-5 flex-none text-gray-400"
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
                        <PopoverButton className="flex items-center gap-x-1 text-sm font-semibold leading-6 text-gray-900">
                            Comedians
                            <ChevronDownIcon
                                aria-hidden="true"
                                className="h-5 w-5 flex-none text-gray-400"
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

                    {currentUser && (
                        <a
                            href={`/profile/${currentUser.id}`}
                            className="text-sm font-semibold leading-6 text-gray-900"
                        >
                            Profile
                        </a>
                    )}

                    {currentUser && currentUser.role == "admin" && (
                        <>
                            <button
                                onClick={() => {
                                    scrapeMenuModal.onOpen();
                                }}
                                className="text-sm font-semibold leading-6 text-gray-900"
                            >
                                Scrape
                            </button>
                        </>
                    )}
                </PopoverGroup>
                <div className="hidden lg:flex lg:flex-1 lg:justify-end">
                    {currentUser ? (
                        <>
                            <button
                                onClick={() => {
                                    signOut();
                                }}
                                className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full"
                            >
                                Log Out
                            </button>
                        </>
                    ) : (
                        <>
                            <div className="hidden lg:flex lg:flex-1 lg:justify-end gap-3">
                                <button
                                    onClick={handleLoginClick}
                                    className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full"
                                >
                                    Log In
                                </button>

                                <button
                                    onClick={handleSignupClick}
                                    className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full"
                                >
                                    Sign Up
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </nav>

            <Dialog
                open={mobileMenuOpen}
                onClose={setMobileMenuOpen}
                className="lg:hidden"
            >
                <div className="fixed inset-0 z-10" />
                <DialogPanel className="fixed inset-y-0 right-0 z-10 w-full overflow-y-auto bg-white px-6 py-6 sm:max-w-sm sm:ring-1 sm:ring-gray-900/10">
                    <div className="flex items-center justify-between">
                        <button
                            type="button"
                            onClick={() => setMobileMenuOpen(false)}
                            className="-m-2.5 rounded-md p-2.5 text-gray-700"
                        >
                            <span className="sr-only">Close menu</span>
                            <XMarkIcon aria-hidden="true" className="h-6 w-6" />
                        </button>
                    </div>
                    <div className="mt-6 flow-root">
                        <div className="-my-6 divide-y divide-gray-500/10">
                            <div className="space-y-2 py-6">
                                <a
                                    href="/"
                                    className="-mx-3 block rounded-lg px-3 py-2 text-base font-semibold leading-7 text-gray-900 hover:bg-gray-50"
                                >
                                    Home
                                </a>
                                <Disclosure as="div" className="-mx-3">
                                    <DisclosureButton className="group flex w-full items-center justify-between rounded-lg py-2 pl-3 pr-3.5 text-base font-semibold leading-7 text-gray-900 hover:bg-gray-50">
                                        Clubs
                                        <ChevronDownIcon
                                            aria-hidden="true"
                                            className="h-5 w-5 flex-none group-data-[open]:rotate-180"
                                        />
                                    </DisclosureButton>
                                </Disclosure>
                                <Disclosure as="div" className="-mx-3">
                                    <DisclosureButton className="group flex w-full items-center justify-between rounded-lg py-2 pl-3 pr-3.5 text-base font-semibold leading-7 text-gray-900 hover:bg-gray-50">
                                        Comedians
                                        <ChevronDownIcon
                                            aria-hidden="true"
                                            className="h-5 w-5 flex-none group-data-[open]:rotate-180"
                                        />
                                    </DisclosureButton>
                                </Disclosure>
                            </div>
                            <div className="flex flex-col py-6 gap-5">
                                {currentUser ? (
                                    <>
                                        <button
                                            onClick={() => {
                                                signOut();
                                            }}
                                            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full"
                                        >
                                            Log Out
                                        </button>
                                    </>
                                ) : (
                                    <>
                                        <button
                                            onClick={handleLoginClick}
                                            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full"
                                        >
                                            Log In
                                        </button>

                                        <button
                                            onClick={handleSignupClick}
                                            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full"
                                        >
                                            Sign Up
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                </DialogPanel>
            </Dialog>
        </header>
    );
};

export default Header;
