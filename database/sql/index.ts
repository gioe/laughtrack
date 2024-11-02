import { join } from "path";
import pkg from "pg-promise";
import path from "path";
import { fileURLToPath } from "url";
import { createSingleton } from "../../util/singletonUtil";

export const clubs = {
    // Create Table
    create: sql("clubs/create.sql").qf,

    // GETs
    getAllShowPopularityData: sql("clubs/getAllShowPopularityData.sql").qf,
    getByName: sql("clubs/getByName.sql").qf,
    getCities: sql("clubs/getCities.sql").qf,
};

export const comedians = {
    // Create Table
    create: sql("comedians/create.sql").qf,

    // GETs
    getAllWithSocialData: sql("comedians/getAllWithSocialData.sql").qf,
    getAllSocialData: sql("comedians/getAllSocialData.sql").qf,
    getAllWithFavoritesAndSocialData: sql(
        "comedians/getAllWithFavoritesAndSocialData.sql",
    ).qf,
    getAllFavorites: sql("comedians/getAllFavorites.sql").qf,
    getByName: sql("comedians/getByName.sql").qf,
    getTrending: sql("comedians/getTrending.sql").qf,
    getAllIdsByUuids: sql("comedians/getAllIdsByUuids.sql").qf,
};

export const favorites = {
    // Create Table
    create: sql("favorites/create.sql").qf,

    // POST
    add: sql("favorites/add.sql").qf,

    // DELETE
    remove: sql("favorites/remove.sql").qf,
};

export const groups = {
    // Create Table
    create: sql("groups/comedianGroupCreate.sql").qf,

    // POST
    add: sql("groups/add.sql").qf,
};

export const lineups = {
    // Create Table
    create: sql("lineups/create.sql").qf,

    getByComedianId: sql("lineups/getByComedianId.sql").qf,
    getByShowId: sql("lineups/getByShowId.sql").qf,
};

export const search = {
    getHomeSearchResults: sql("search/getHomeSearchResults.sql").qf,
};

export const shows = {
    // Create Table
    create: sql("shows/create.sql").qf,

    //POST
    add: sql("shows/add.sql").qf,

    // GETs
    getAllLineupPopularityData: sql("shows/getAllLineupPopularityData.sql").qf,
    getWithLineup: sql("shows/getWithLineup.sql").qf,

    //DELETE

    deleteByClub: sql("shows/deleteByClub.sql").qf,
};

export const tags = {
    // Create Tables
    create: sql("tags/create.sql").qf,
    createClubTags: sql("tags/createClubTags.sql").qf,
    createComedianTags: sql("tags/createComedianTags.sql").qf,
    createShowTags: sql("tags/createShowTags.sql").qf,

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
