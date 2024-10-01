'use client'

import { useCallback, useState } from "react"
import MenuItem from "./MenuItem"
import useRegisterModal from "@/hooks/useRegisterModel"
import useLoginModal from "@/hooks/useLoginModal"
import { User } from "@/types/user"
import { signOut } from "next-auth/react"
import { MenuIcon, UserCircleIcon, UsersIcon } from "@heroicons/react/solid";

interface UserMenuProps {
    currentUser?: User | null;
}

const UserMenu: React.FC<UserMenuProps> = ({
    currentUser
}) => {

    const loginModal = useLoginModal();
    const registerModal = useRegisterModal();
    const [isOpen, setIsOpen] = useState(false);

    const toggleOpen = useCallback(() => {
        setIsOpen((value => !value));
    }, [])

    const handleLoginClick = useCallback(() => {
        setIsOpen((value => !value));
        loginModal.onOpen()
    }, [loginModal])

    const handleSignupClick = useCallback(() => {
        setIsOpen((value => !value));
        registerModal.onOpen()
    }, [registerModal])

    return (
        <div>
            <div
                onClick={toggleOpen}
                className="flex items-center space-x-2 border-2 p-2 rounded-full">
                <MenuIcon className="h-6" />
                <UserCircleIcon className="h-6" />
            </div>
            {isOpen && (
                <div className="absolute rounded-xl shadow-md w-[100vw] md:w-1/4 bg-white overflow-hidden right-0 top-25 text-sm">
                    <div className="flex flex-col cursor-pointer">
                        {currentUser ? (
                            <>
                                <MenuItem
                                    onClick={() => {}}
                                    label="Favorite comedians"
                                />
                                <hr />
                                <MenuItem
                                    onClick={() => signOut()}
                                    label="Logout"
                                />
                            </>
                        ) : (
                            <>
                                <MenuItem
                                    onClick={handleLoginClick}
                                    label="Login"
                                />
                                <MenuItem
                                    onClick={handleSignupClick}
                                    label="Sign up"
                                />
                            </>
                        )}

                    </div>
                </div>
            )}
        </div>
    )
}

export default UserMenu;