import { ButtonType } from "../enum/buttonType";
import type { LucideIcon } from "lucide-react";

export interface ButtonData {
    type: ButtonType;
    label: string;
    icon?: LucideIcon;
    styling?: ButtonStyling;
}

export interface ButtonStyling {
    backgroundColor: string;
}
