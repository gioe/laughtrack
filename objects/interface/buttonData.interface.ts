import { ButtonType } from "../enum/buttonType";
import { IconType } from "react-icons";

export interface ButtonData {
    type: ButtonType;
    label: string;
    icon?: IconType;
    styling?: ButtonStyling
}

export interface ButtonStyling {
    backgroundColor: string;
}
