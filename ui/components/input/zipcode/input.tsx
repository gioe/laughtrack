import React from "react";

const ZipCodeInput = ({
    id = "zipcode",
    placeholder = "Enter your zip code...",
}) => {
    return (
        <div className="space-y-2">
            <input
                type="text"
                id={id}
                placeholder={placeholder}
                maxLength={5}
                pattern="[0-9]{5}"
                className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white`}
            />
        </div>
    );
};

export default ZipCodeInput;
