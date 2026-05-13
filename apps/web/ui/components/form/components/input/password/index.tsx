import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input, InputProps } from "../../../../ui/input";

const PasswordInput = (props: InputProps) => {
    const [showPassword, setShowPassword] = useState(false);

    return (
        <div className="space-y-2">
            <div className="relative">
                <Input
                    type={showPassword ? "text" : "password"}
                    inputTextColor="text-foreground"
                    className={`w-full px-3 py-2 border border-white/15 rounded-lg focus:ring-2 focus:ring-copper focus:border-copper text-sm bg-white/5 placeholder:text-white/40`}
                    {...props}
                />
                <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/50 hover:text-white/80"
                    aria-label={
                        showPassword ? "Hide password" : "Show password"
                    }
                >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
            </div>
        </div>
    );
};

export default PasswordInput;
