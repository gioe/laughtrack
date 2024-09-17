'use client';

import { SearchIcon } from "@heroicons/react/solid";

interface SearchProps {
    searchInput: string;
    handleSeachInputChange: (value: string) => void
    placeholder?: string;
}
const Search: React.FC<SearchProps> = ({
    searchInput,
    handleSeachInputChange,
    placeholder
}) => {

    return (
        <div className="flex items-center md:border-2 rounded-full py-2 md:shadow-sm">
            <input 
                value={searchInput}
                onChange={(e) => handleSeachInputChange(e.target.value)}
                className="flex-grow pl-5 bg-transparent outline-none text-sm text-gray-600 placeholde-gray-400"
                type="text" 
                placeholder={placeholder ?? "Search by city"}>
            </input>
            <SearchIcon className="hidden md:inline-flex h-8 bg-red-400 text-white rounded-full p-2 cursor-pointer md:mx-2" />
        </div>
    )
}

export default Search;