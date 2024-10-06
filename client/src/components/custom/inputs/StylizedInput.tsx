'use client';

import { FieldErrors, FieldValues, UseFormRegister } from "react-hook-form";
import {Input} from "@nextui-org/react";

interface StylizedInputProps {
    id: string;
    label: string;
    type?: string;
    disabled?: boolean;
    required?: boolean;
    register: UseFormRegister<FieldValues>;
    errors: FieldErrors;
}

const StylizedInput: React.FC<StylizedInputProps> = ({
    id,
    label,
    type = 'text', 
    disabled, 
    register,
    required,
    errors
}) => {
    return (
        <div className="w-full relative"> 
        <Input 
            id={id} 
            label={label}
            disabled={disabled} 
            {...register(id, { required })}
            type={type}
        />
        </div>
    )
}

export default StylizedInput;