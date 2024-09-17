'use client';

import { User } from "@/types/user";
import Logo from "./Logo";
import Search from "./Search";
import UserMenu from "./UserMenu";
import React, { useState } from "react";
import 'react-date-range/dist/styles.css'; // main style file
import 'react-date-range/dist/theme/default.css'; // theme css file
import { DateRangePicker, RangeKeyDict } from 'react-date-range';

interface NavbarProps {
    currentUser?: User | null;
}

const Navbar: React.FC<NavbarProps> = ({
    currentUser
}) => {

    const [searchInput, setSearchInput] = useState("")
    const [startDate, setStartDate] = useState(new Date())
    const [endDate, setEndDate] = useState(new Date())

    const selectionRange = {
        startDate,
        endDate,
        key: 'selection'
    }

    const handleDateSelection = (ranges: RangeKeyDict) => {
        setStartDate(ranges.selection.startDate as Date)
        setEndDate(ranges.selection.endDate as Date)
    }

    const handleSearchClick = () => {

    }

    const handleCancelClick = () => {
        setSearchInput("")
        setStartDate(new Date())
        setEndDate(new Date())
    }

    return (
        <header className="sticky top-0 z-50 grid grid-cols-3 bg-white shadow-md p-5 md:px-10">
            <div className="relative flex items-center h-10 cursor-pointer my-auto">
                <Logo />
            </div>
            <Search
                searchInput={searchInput}
                handleSeachInputChange={(value: string) => {
                    console.log(value)
                    setSearchInput(value)
                }} />
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
                        <button
                            onClick={handleSearchClick}
                            className="flex-grow text-red-400">
                            Search
                        </button>
                    </div>
                </div>
            )}
        </header>
    )
}

export default Navbar;