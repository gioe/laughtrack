"use client";

import ButtonComponent from "../../../button/form";
import { ButtonType } from "../../../../objects/enum";

interface DefaultFormButtonProps {
    label: string;
}

export function DefaultFormButton({ label }: DefaultFormButtonProps) {
    return (
        <ButtonComponent
            data={{
                type: ButtonType.Submit,
                label,
            }}
        />
    );
}
