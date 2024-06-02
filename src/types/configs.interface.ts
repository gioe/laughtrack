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