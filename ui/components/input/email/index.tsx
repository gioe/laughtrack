import React from "react";

const EmailInput = ({
    id = "email",
    label = "Email",
    placeholder = "Enter your email...",
    value,
    onChange,
    className = "",
}) => {
    return (
        <div className="space-y-2">
            <input
                type="email"
                id={id}
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white ${className}`}
            />
        </div>
    );
};

export default EmailInput;
