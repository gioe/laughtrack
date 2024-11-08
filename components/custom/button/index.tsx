"use client";

import { IconType } from "react-icons";
import { Button } from "../../ui/button";

interface ButtonProps {
    label: string;
    onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
    disabled?: boolean;
    outline?: boolean;
    small?: boolean;
    icon?: IconType;
    type?: "submit" | "reset" | "button" | undefined;
}

const ButtonComponent: React.FC<ButtonProps> = ({
    type,
    label,
    onClick,
    disabled,
    outline,
    small,
    icon: Icon,
}) => {
    return (
        <Button
            type={type}
            onClick={onClick}
            disabled={disabled}
            className={`relative disabled:opacity-70 disabled:cursor-not-allowed rounded-lg hover:opacity-80 transition w-full
                 ${outline ? "bg-white" : "bg-red-500"}
                 ${outline ? "border-black" : "bg-red-500"}
                ${outline ? "text-black" : "text-white"}
                ${small ? "py-1" : "py-3"}
                 ${small ? "text-sm" : "text-md"}
                 ${small ? "font-light" : "font-semibold"}
                 ${small ? "border-[1px]" : "border-2"}
                `}
        >
            {Icon && <Icon size={24} className="absolute left-4 top-3"></Icon>}
            {label}
        </Button>
    );
};

export default ButtonComponent;
