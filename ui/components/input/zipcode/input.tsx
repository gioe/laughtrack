import React from "react";

const ZipCodeInput = ({
    id = "zipcode",
    label = "Zip Code",
    placeholder = "Enter your zip code...",
    value,
    onChange,
    className = "",
}) => {
    // Handle input to only allow numbers
    const handleChange = (e) => {
        const value = e.target.value.replace(/\D/g, "");
        if (onChange) {
            e.target.value = value;
            onChange(e);
        }
    };

    return (
        <div className="space-y-2">
            <label
                htmlFor={id}
                className="block text-sm font-bold text-gray-900"
            >
                {label}
            </label>
            <input
                type="text"
                id={id}
                value={value}
                onChange={handleChange}
                placeholder={placeholder}
                maxLength={5}
                pattern="[0-9]{5}"
                className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white ${className}`}
            />
        </div>
    );
};

export default ZipCodeInput;
