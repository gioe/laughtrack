import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
    extends React.InputHTMLAttributes<HTMLInputElement> {
    inputTextColor?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
    ({ className, type, inputTextColor = "text-black", ...props }, ref) => {
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
                    inputTextColor,
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
