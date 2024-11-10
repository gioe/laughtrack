import { join } from "path";
import pkg from "pg-promise";
import path from "path";
import { fileURLToPath } from "url";
import { createSingleton } from "../../util/singletonUtil";

export const clubs = {
    // Create Table
    createTabe: sql("clubs/create.sql").qf,

    // GETs
    getAllShowPopularityData: sql("clubs/getAllShowPopularityData.sql").qf,
    getByName: sql("clubs/getByName.sql").qf,
    getById: sql("clubs/getById.sql").qf,
    getCities: sql("clubs/getCities.sql").qf,
    getSearchResults: sql("clubs/getSearchResults.sql").qf,
    getAllInCity: sql("clubs/getAllInCity.sql").qf,

};

export const comedians = {
    // Create Table
    createTabe: sql("comedians/create.sql").qf,

    // GETs
    getAllWithSocialData: sql("comedians/getAllWithSocialData.sql").qf,
    getAllSocialData: sql("comedians/getAllSocialData.sql").qf,
    getAllWithFavoritesAndSocialData: sql(
        "comedians/getAllWithFavoritesAndSocialData.sql",
    ).qf,
    getAllFavorites: sql("comedians/getAllFavorites.sql").qf,
    getByName: sql("comedians/getByName.sql").qf,
    getById: sql("comedians/getById.sql").qf,
    getTrending: sql("comedians/getTrending.sql").qf,
    getAllIdsByUuids: sql("comedians/getAllIdsByUuids.sql").qf,
    getSearchResults: sql("comedians/getSearchResults.sql").qf,

};

export const lineupItems = {
    // Create Table
    createTabe: sql("lineupItems/create.sql").qf,
    getByComedianId: sql("lineupItems/getByComedianId.sql").qf,
    getByShowId: sql("lineupItems/getByShowId.sql").qf,
};

export const favorites = {
    // Create Table
    createTabe: sql("favorites/create.sql").qf,

    // POST
    add: sql("favorites/add.sql").qf,

    // DELETE
    remove: sql("favorites/remove.sql").qf,
};

export const shows = {
    // Create Table
    createTabe: sql("shows/create.sql").qf,

    //POST
    add: sql("shows/add.sql").qf,

    // GETs
    getAllLineupPopularityData: sql("shows/getAllLineupPopularityData.sql").qf,
    getWithLineup: sql("shows/getWithLineup.sql").qf,
    getSearchResults: sql("shows/getSearchResults.sql").qf,
    getByTicketLink: sql("shows/geByTicketLink.sql").qf,


    //DELETE
    deleteByClub: sql("shows/deleteByClub.sql").qf,
};

export const tags = {
    // Create Tables
    createTabe: sql("tags/create.sql").qf,
    createTaggedClubsTable: sql("tags/createTaggedClubs.sql").qf,
    createTaggedComediansTable: sql("tags/createTaggedComedians.sql").qf,
    createTaggedShowsTable: sql("tags/createTaggedShows.sql").qf,

    // GET
    getAllByType: sql("tags/getAllByType.sql").qf,
};

export const users = {
    // Create Table
    create: sql("users/create.sql").qf,

    //POST
    add: sql("users/add.sql").qf,
};

interface IQueryFileScope {
    qf: pkg.QueryFile;
}

///////////////////////////////////////////////
// Helper for linking to external query files;
function sql(file: string): IQueryFileScope {

    return createSingleton<IQueryFileScope>(file, () => {
        const __filename = fileURLToPath(import.meta.url); // get the resolved path to the file
        const __dirname = path.dirname(__filename);
        const fullPath: string = join(__dirname, file); // generating full path;

        const qf = new pkg.QueryFile(fullPath, {
            minify: true,
        });

        if (qf.error) console.error(qf.error);

        return {
            qf
        };
    })
}
