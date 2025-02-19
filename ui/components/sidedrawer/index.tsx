"use client";
import {
    Dialog,
    DialogPanel,
    Disclosure,
    DisclosureButton,
} from "@headlessui/react";
import { XButton } from "../button/x";
import { useCallback } from "react";
import { HeaderItem } from "../navbar/headerItem";
import { ChevronDownIcon } from "@heroicons/react/24/solid";
import { FullRoundedButton } from "../button/rounded/full";
import { useSignOut } from "@/hooks/useSignOut";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { useLoginModal } from "@/hooks";

interface SideDrawerProps {
    onClose: (open: boolean) => void;
    open: boolean;
    currentUser?: UserProfileInterface | null;
}

export function SideDrawer({ open, onClose, currentUser }: SideDrawerProps) {
    const loginModal = useLoginModal();
    const handleSignOut = useSignOut();

    const handleLoginClick = useCallback(() => {
        loginModal.onOpen();
    }, [loginModal]);

    return (
        <Dialog open={open} onClose={onClose} className="lg:hidden">
            <div className="fixed inset-0 z-10" />
            <DialogPanel className="fixed inset-y-0 right-0 z-10 w-full overflow-y-auto bg-white px-6 py-6 sm:max-w-sm sm:ring-1 sm:ring-gray-900/10">
                <div className="flex items-center justify-start">
                    <XButton handleClick={() => onClose(false)} />
                </div>
                <div className="mt-6 flow-root">
                    <div className="-my-6 divide-y divide-gray-500/10">
                        <div className="space-y-2 py-6">
                            <HeaderItem
                                highlighted={false}
                                href="/"
                                title="Home"
                            />

                            <Disclosure as="div" className="-mx-3">
                                <DisclosureButton
                                    className="group flex w-full
                                items-center justify-between
                                rounded-lg py-2 pl-3 pr-3.5 text-base leading-7
                                 text-gray-900 hover:bg-gray-50"
                                >
                                    <HeaderItem
                                        highlighted={false}
                                        title="Clubs"
                                    />
                                    <ChevronDownIcon
                                        aria-hidden="true"
                                        className="h-5 w-5 flex-none text-soft-charcoal"
                                    />
                                </DisclosureButton>
                            </Disclosure>
                            <Disclosure as="div" className="-mx-3">
                                <DisclosureButton
                                    className="group flex w-full
                                items-center justify-between
                                rounded-lg py-2 pl-3 pr-3.5 text-base leading-7
                                 text-gray-900 hover:bg-gray-50"
                                >
                                    <HeaderItem
                                        highlighted={false}
                                        title="Comedians"
                                    />
                                    <ChevronDownIcon
                                        aria-hidden="true"
                                        className="h-5 w-5 flex-none text-soft-charcoal"
                                    />
                                </DisclosureButton>
                            </Disclosure>
                        </div>
                        <div className="flex flex-col py-6 gap-5">
                            {currentUser ? (
                                <FullRoundedButton
                                    handleClick={handleSignOut}
                                    label="Log Out"
                                />
                            ) : (
                                <>
                                    <FullRoundedButton
                                        handleClick={handleLoginClick}
                                        label="Log In"
                                    />

                                    {/* <FullRoundedButton
                                        handleClick={handleSignupClick}
                                        label="Sign Up"
                                    /> */}
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </DialogPanel>
        </Dialog>
    );
}
