/* eslint-disable @typescript-eslint/no-empty-object-type */
import * as React from "react";
import { useStyleContext } from "@/contexts/StyleProvider";

export interface InputProps
    extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
    ({ className, type, ...props }, ref) => {
        const { getCurrentStyles } = useStyleContext();
        const styleConfig = getCurrentStyles();
        return (
            <input
                type={type}
                className={`border-transparent bg-transparent transition-colors text-[18px] rounded-lg font-dmSans 
                    focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring 
                    disabled:cursor-not-allowed disabled:opacity-50
                    focus:ring-2 focus:ring-blue-500 focus:bg-transparent focus:outline-none 
                    placeholder:font-dmSans placeholder:text-[18px]
                    ${styleConfig.inputTextColor}`}
                ref={ref}
                {...props}
            />
        );
    },
);
Input.displayName = "Input";

export { Input };
