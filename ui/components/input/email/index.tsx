import React from "react";

const EmailInput = ({ id = "email", placeholder = "Enter your email..." }) => {
    return (
        <div className="space-y-2">
            <input
                type="email"
                id={id}
                placeholder={placeholder}
                className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white`}
            />
        </div>
    );
};

export default EmailInput;
