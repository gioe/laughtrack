import React from "react";
import { Input, InputProps } from "../../../../ui/input";

const EmailInput = (props: InputProps) => {
    return (
        <div className="space-y-2">
            <Input
                type="email"
                inputTextColor="text-foreground"
                className={`w-full px-3 py-2 border border-white/15
                    rounded-lg focus:ring-2 focus:ring-copper
                    focus:border-copper text-sm bg-white/5
                    placeholder:text-white/40`}
                {...props}
            />
        </div>
    );
};

export default EmailInput;
