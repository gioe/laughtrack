import { Club } from "./club.interface.js";

export interface HTMLConfigurable extends Club {
    scraper: string;
    dateMenuSelector: string;
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
    dateMenuOptionSelector: string;
    optionValueAttribute: string;
    extraTimeString: string;
    extraDateString: string;
}
