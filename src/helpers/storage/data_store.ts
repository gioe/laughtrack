import { ClubConfig } from "../../types/index.js";

export const writeToDatabase = (object: any, clubConfig: ClubConfig) => {
    console.log(`Writing to ${clubConfig.name}`);
    }