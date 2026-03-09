import React from "react";
import { Input, InputProps } from "../../../../ui/input";

const ZipCodeInput = (props: InputProps) => {
    return (
        <div className="space-y-2">
            <Input
                type="text"
                maxLength={5}
                pattern="[0-9]{5}"
                className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white`}
                {...props}
            />
        </div>
    );
};

export default ZipCodeInput;
