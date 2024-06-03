import { Club } from "./club.interface.js";

export interface HTMLConfigurable extends Club {
    allDateOptionsSelector: string;
    dateMenuSelector:string;
    allShowsSelector: string;

    lineupsParentSelector: string;
    lineupItemsSelector: string;
    setContentSelector: string;
    selectedDateSelector: string;
    selectedTimeSelector: string;
    selectedOptionalShowNameSelector: string;
    dateOptionSelector: string;
    comedianNameSelector: string;
    comedianWebsiteSelector: string;
    comedianHeadshotSelector: string;
    optionValueAttribute: string;
    extraTimeString: string;
    extraDateString: string;
}
