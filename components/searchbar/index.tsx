import React from "react";
import { MapPin, Calendar, Search } from "lucide-react";
import { CircleIconButton } from "../button/circleIcon";

const SearchBar = () => {
    return (
        <div className="flex items-center w-full max-w-3xl bg-white/20 backdrop-blur rounded-full">
            {/* City Input */}
            <div className="flex-1 flex items-center px-6 border-r border-gray-600/50">
                <MapPin className="w-5 h-5 text-gray-400 mr-3" />
                <input
                    type="text"
                    placeholder="When"
                    className="w-full bg-transparent text-white placeholder-gray-400 focus:outline-none outline-none py-4"
                />
            </div>

            {/* Date Input */}
            <div className="flex-1 flex items-center px-6">
                <Calendar className="w-5 h-5 text-gray-400 mr-3" />
                <input
                    type="text"
                    placeholder="When"
                    className="w-full bg-transparent text-white placeholder-gray-400 focus:outline-none outline-none py-4"
                />
            </div>
            <CircleIconButton>
                <Search className="w-5 h-5 text-white" />
            </CircleIconButton>
        </div>
    );
};

export default SearchBar;
