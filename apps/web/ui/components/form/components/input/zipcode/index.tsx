import React from "react";
import { Input, InputProps } from "../../../../ui/input";

const ZipCodeInput = (props: InputProps) => {
    return (
        <div className="space-y-2">
            <Input
                type="text"
                maxLength={5}
                pattern="[0-9]{5}"
                inputTextColor="text-foreground"
                className={`w-full px-3 py-2 border border-white/15 rounded-lg focus:ring-2 focus:ring-copper focus:border-copper text-sm bg-white/5 placeholder:text-white/40`}
                {...props}
            />
        </div>
    );
};

export default ZipCodeInput;
