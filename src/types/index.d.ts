export interface Club {
    name: string;
    website: string;
}

export interface Show {
    club: Club;
    dateTime: string;
    name: string;
    comedians: Comedian[];
}

export interface Comedian { 
    name: string;
    website: string;
}

interface ClubConfig {
    name: string;
    website: string;
    scraper: string;
    timezone: string;
    htmlConfig: HTMLConfig;
    textConfig: TextConfig;
}

interface HTMLConfig {
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
}

interface TextConfig {
    extraTimeString: string;
    extraDateString: string;
}