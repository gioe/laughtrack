"use client";

import { IconType } from "react-icons";
import { Button } from "../ui/button";
import { ButtonData } from "../../objects/interface";

interface ButtonProps {
    data: ButtonData;
    onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
    disabled?: boolean;
    icon?: IconType;
}

const ButtonComponent: React.FC<ButtonProps> = ({
    data,
    disabled,
    icon: Icon,
    onClick,
}) => {
    return (
        <Button
            type={data.type}
            disabled={disabled}
            className={`disabled:opacity-70
                 disabled:cursor-not-allowed rounded-lg hover:opacity-80
                 transition w-4/5 bg-${data.styling?.backgroundColor ?? "red-500"}
                text-white mt-5 font-semibold border-2`}
        >
            {Icon && <Icon size={24} className="absolute left-4 top-3"></Icon>}
            {data.label}
        </Button>
    );
};

export default ButtonComponent;
