'use client';

import UserMenu from "./UserMenu";
import React from "react";
import Logo from "./Logo";
import { UserInterface } from "@/interfaces/user.interface";

interface NavbarProps {
    currentUser?: UserInterface | null;
}

const Header: React.FC<NavbarProps> = ({
    currentUser,
}) => {


    return (
        <header className="sticky top-0 z-50 grid grid-cols-2 bg-silver-gray shadow-md p-5 md:px-10">
            <div className="relative flex items-center h-10 cursor-pointer my-auto">
            <Logo />

            </div>
            <div className="flex space-x-4 items-center justify-end text-gray-500">
                <UserMenu currentUser={currentUser} />
            </div>
        </header>
    )
}

export default Header;