'use client';

import { User } from "@/types/user";
import UserMenu from "./UserMenu";
import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Logo from "./Logo";
import Link from "next/link";

interface NavbarProps {
    currentUser?: User | null;
}

const Header: React.FC<NavbarProps> = ({
    currentUser,
}) => {

    const router = useRouter();

    const [searchInput, setSearchInput] = useState("")
    const [startDate, setStartDate] = useState(new Date())
    const [endDate, setEndDate] = useState(new Date())

    const startDateString = startDate.toISOString();
    const endDateString = endDate.toISOString();

    const selectionRange = {
        startDate,
        endDate,
        key: 'selection'
    }

    const handleSearchClick = () => {
        if (searchInput == "") {
            return;
        }
    }

    const handleCancelClick = () => {
        setSearchInput("")
        setStartDate(new Date())
        setEndDate(new Date())
    }

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