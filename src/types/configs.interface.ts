import { Club } from "./club.interface.js";

export interface HTMLConfiguration {
    allDateOptionsSelector: string;
    dateMenuSelector: string;
    allShowsSelector: string
    selectedTimeSelector: string;
    selectedOptionalShowNameSelector: string,
    extraTimeString: string,
    extraDateString: string,
    setContentSelector: string,
    comedianWebsiteSelector: string,
    comedianNameSelector: string
}

export interface HTMLConfigurable {
    htmlConfig: HTMLConfiguration;
}
