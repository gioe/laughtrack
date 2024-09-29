'use client';

import { User } from "@/types/user";
import UserMenu from "./UserMenu";
import React, { useState } from "react";
import 'react-date-range/dist/styles.css'; // main style file
import 'react-date-range/dist/theme/default.css'; // theme css file
import 'mapbox-gl/dist/mapbox-gl.css';
import { DateRangePicker, RangeKeyDict } from 'react-date-range';
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

    const handleDateSelection = (ranges: RangeKeyDict) => {
        setStartDate(ranges.selection.startDate as Date)
        setEndDate(ranges.selection.endDate as Date)
    }

    const handleLogoClick = () => {
        router.push('/')
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
                <Logo onClick={handleLogoClick} />
            </div>
            <div className="flex space-x-4 items-center justify-end text-gray-500">
                <UserMenu currentUser={currentUser} />
            </div>
            {searchInput && (
                <div className="flex flex-col col-span-3 mx-auto">
                    <DateRangePicker
                        className="flex"
                        ranges={[selectionRange]}
                        minDate={new Date()}
                        rangeColors={['#FD5B61']}
                        onChange={handleDateSelection}
                    />
                    <div className="flex">
                        <button
                            onClick={handleCancelClick}
                            className="flex-grow text-gray-500">
                            Cancel
                        </button>
                        {searchInput ? (
                            <Link
                                className="flex-grow text-red-400 text-center"
                                href={{
                                    pathname: '/show/search',
                                    query: {
                                        location: searchInput,
                                        startDate: startDateString,
                                        endDate: endDateString,
                                    }
                                }}
                            >
                                Search
                            </Link>
                        ) : (
                            <button
                                onClick={handleSearchClick}
                                className="flex-grow text-red-400">
                                Search
                            </button>
                        )}
                    </div>
                </div>
            )}
        </header>
    )
}

export default Header;