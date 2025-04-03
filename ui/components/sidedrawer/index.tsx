"use client";
import {
    Dialog,
    DialogPanel,
    Disclosure,
    DisclosureButton,
} from "@headlessui/react";
import { XButton } from "../button/x";
import { useCallback } from "react";
import { FullRoundedButton } from "../button/rounded/full";
import { useSignOut } from "@/hooks/useSignOut";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { useLoginModal } from "@/hooks";
import { SideDrawerItem } from "./item";
import { usePathname } from "next/navigation";

interface SideDrawerProps {
    onClose: (open: boolean) => void;
    open: boolean;
    currentUser?: UserProfileInterface | null;
}

export function SideDrawer({ open, onClose, currentUser }: SideDrawerProps) {
    const pathname = usePathname();
    const loginModal = useLoginModal();
    const handleSignOut = useSignOut();

    const handleLoginClick = useCallback(() => {
        loginModal.onOpen();
        onClose(false); // Close drawer after clicking login
    }, [loginModal, onClose]);

    return (
        <Dialog
            open={open}
            onClose={onClose}
            className="lg:hidden relative z-30"
        >
            <div className="fixed inset-0 bg-black/25 backdrop-blur-sm" />
            <DialogPanel className="fixed inset-y-0 right-0 z-40 w-full overflow-y-auto bg-coconut-cream px-4 sm:px-6 py-4 sm:py-6 sm:max-w-sm sm:ring-1 sm:ring-gray-900/10 shadow-xl transition-transform duration-300">
                <div className="flex items-center justify-between">
                    <span className="text-xl font-bold font-gilroy-bold">
                        Laughtrack
                    </span>
                    <button
                        type="button"
                        className="p-2 rounded-md text-gray-500 hover:text-gray-700"
                        onClick={() => onClose(false)}
                    >
                        <XButton handleClick={() => onClose(false)} />
                    </button>
                </div>
                <div className="mt-6 flow-root">
                    <div className="-my-6 divide-y divide-gray-500/10">
                        <div className="space-y-2 py-6">
                            <SideDrawerItem
                                title="Home"
                                href="/"
                                highlighted={pathname === "/"}
                            />
                            <SideDrawerItem
                                title="Shows"
                                href="/show/search"
                                highlighted={pathname.includes("/show")}
                            />
                            <SideDrawerItem
                                title="Clubs"
                                href="/club/search"
                                highlighted={pathname.includes("/club")}
                            />
                            <SideDrawerItem
                                title="Comedians"
                                href="/comedian/search"
                                highlighted={pathname.includes("/comedian")}
                            />
                        </div>
                        <div className="flex flex-col py-6 gap-5">
                            {currentUser ? (
                                <>
                                    <SideDrawerItem
                                        title="Profile"
                                        href={`/profile/${currentUser.id}`}
                                        highlighted={pathname.includes(
                                            "/profile",
                                        )}
                                    />
                                    <FullRoundedButton
                                        handleClick={handleSignOut}
                                        label="Log Out"
                                    />
                                </>
                            ) : (
                                <FullRoundedButton
                                    handleClick={handleLoginClick}
                                    label="Log In"
                                />
                            )}
                        </div>
                    </div>
                </div>
            </DialogPanel>
        </Dialog>
    );
}
