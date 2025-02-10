import React from "react";
import { Input } from "../../../../ui/input";

const EmailInput = (props) => {
    return (
        <div className="space-y-2">
            <Input
                type="email"
                className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white`}
                {...props}
            />
        </div>
    );
};

export default EmailInput;
