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
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";

interface SideDrawerProps {
    onClose: (open: boolean) => void;
    open: boolean;
    currentUser?: UserProfileInterface | null;
}

export function SideDrawer({ open, onClose, currentUser }: SideDrawerProps) {
    const pathname = usePathname();
    const loginModal = useLoginModal();
    const handleSignOut = useSignOut();
    const prefersReducedMotion = useReducedMotion();

    const handleLoginClick = useCallback(() => {
        loginModal.onOpen();
        onClose(false); // Close drawer after clicking login
    }, [loginModal, onClose]);

    const menuItems = [
        { title: "Home", href: "/", highlighted: pathname === "/" },
        {
            title: "Shows",
            href: "/show/search",
            highlighted: pathname.includes("/show"),
        },
        {
            title: "Clubs",
            href: "/club/search",
            highlighted: pathname.includes("/club"),
        },
        {
            title: "Comedians",
            href: "/comedian/search",
            highlighted: pathname.includes("/comedian"),
        },
    ];

    const sideDrawerVariants = {
        hidden: { x: prefersReducedMotion ? 0 : "100%", opacity: 0 },
        visible: {
            x: 0,
            opacity: 1,
            transition: prefersReducedMotion
                ? { duration: 0 }
                : { type: "spring", damping: 25, stiffness: 300 },
        },
        exit: {
            x: prefersReducedMotion ? 0 : "100%",
            opacity: 0,
            transition: prefersReducedMotion
                ? { duration: 0 }
                : { type: "spring", damping: 30, stiffness: 300 },
        },
    };

    const itemVariants = {
        hidden: { opacity: 0, x: prefersReducedMotion ? 0 : 20 },
        visible: (i: number) => ({
            opacity: 1,
            x: 0,
            transition: prefersReducedMotion
                ? { duration: 0 }
                : { delay: i * 0.1, duration: 0.3 },
        }),
    };

    return (
        <AnimatePresence>
            {open && (
                <Dialog
                    open={open}
                    onClose={onClose}
                    className="lg:hidden relative z-30"
                >
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: prefersReducedMotion ? 0 : 0.3 }}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm"
                        onClick={() => onClose(false)}
                    />
                    <DialogPanel className="fixed inset-y-0 right-0 z-40 w-full overflow-y-auto bg-coconut-cream/95 px-4 sm:px-6 py-4 sm:py-6 sm:max-w-sm sm:ring-1 sm:ring-gray-900/10 shadow-xl">
                        <motion.div
                            variants={sideDrawerVariants}
                            initial="hidden"
                            animate="visible"
                            exit="exit"
                            className="h-full flex flex-col"
                        >
                            <div className="flex items-center justify-between">
                                <motion.span
                                    initial={{ opacity: 0, y: prefersReducedMotion ? 0 : -10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: prefersReducedMotion ? 0 : 0.2 }}
                                    className="text-2xl font-bold font-chivo bg-gradient-to-r from-copper to-cedar bg-clip-text text-transparent"
                                >
                                    Laughtrack
                                </motion.span>
                                <motion.button
                                    initial={{ opacity: 0, rotate: prefersReducedMotion ? 0 : -90 }}
                                    animate={{ opacity: 1, rotate: 0 }}
                                    transition={{ delay: prefersReducedMotion ? 0 : 0.3 }}
                                    type="button"
                                    className="p-2 rounded-md text-gray-500 hover:text-gray-700 transition-colors"
                                    onClick={() => onClose(false)}
                                >
                                    <XButton
                                        handleClick={() => onClose(false)}
                                    />
                                </motion.button>
                            </div>
                            <div className="mt-8 flex-1">
                                <div className="space-y-2">
                                    {menuItems.map((item, index) => (
                                        <motion.div
                                            key={item.title}
                                            custom={index}
                                            variants={itemVariants}
                                            initial="hidden"
                                            animate="visible"
                                        >
                                            <SideDrawerItem
                                                title={item.title}
                                                href={item.href}
                                                highlighted={item.highlighted}
                                            />
                                        </motion.div>
                                    ))}
                                </div>
                                <motion.div
                                    variants={itemVariants}
                                    initial="hidden"
                                    animate="visible"
                                    custom={menuItems.length + 1}
                                    className="mt-8"
                                >
                                    {currentUser ? (
                                        <div className="space-y-4">
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
                                        </div>
                                    ) : (
                                        <FullRoundedButton
                                            handleClick={handleLoginClick}
                                            label="Log In"
                                        />
                                    )}
                                </motion.div>
                            </div>
                        </motion.div>
                    </DialogPanel>
                </Dialog>
            )}
        </AnimatePresence>
    );
}
