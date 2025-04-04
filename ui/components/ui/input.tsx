/* eslint-disable @typescript-eslint/no-empty-object-type */
import * as React from "react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { cn } from "@/lib/utils";

export interface InputProps
    extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
    ({ className, type, ...props }, ref) => {
        const { getCurrentStyles } = useStyleContext();
        const styleConfig = getCurrentStyles();
        return (
            <input
                type={type}
                className={cn(
                    `flex w-full border-transparent bg-transparent
                    text-sm sm:text-base leading-normal
                    transition-colors duration-200
                    rounded-lg px-3 py-1.5
                    focus-visible:outline-none focus-visible:ring-1
                    focus-visible:ring-ring focus:ring-2
                    focus:ring-blue-500 focus:outline-none
                    disabled:cursor-not-allowed disabled:opacity-50
                    placeholder:text-sm sm:placeholder:text-base
                    placeholder:text-gray-400`,
                    styleConfig.inputTextColor,
                    className,
                )}
                ref={ref}
                {...props}
            />
        );
    },
);
Input.displayName = "Input";

export { Input };
