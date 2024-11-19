"use client";

import ButtonComponent from "../../../../button";
import { ButtonType } from "../../../../../objects/enum";

interface FormButtonProps {
    label: string;
}

export function FormButton({ label }: FormButtonProps) {
    return (
        <ButtonComponent
            data={{
                type: ButtonType.Submit,
                label,
                styling: {
                    backgroundColor: "bg-silver-gray",
                },
            }}
        />
    );
}
