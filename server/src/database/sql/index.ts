import { IQueryFileOptions } from 'pg-promise';
import { join } from 'path';
import pkg from 'pg-promise';
import path from 'path';
import { fileURLToPath } from 'url';

export const clubs = {
    // Create Table
    create: sql('clubs/create.sql'),

    // GETs
    getAllShowPopularityData: sql('clubs/getAllShowPopularityData.sql'),
    getByName: sql('clubs/getByName.sql'),
    getCities: sql('clubs/getCities.sql')
}

export const comedians = {
    // Create Table
    create: sql('comedians/create.sql'),

    // GETs
    getAllWithSocialData: sql('comedians/getAllWithSocialData.sql'),
    getAllSocialData: sql('comedians/getAllSocialData.sql'),
    getAllWithFavoritesAndSocialData: sql('comedians/getAllWithFavoritesAndSocialData.sql'),
    getAllFavorites: sql('comedians/getAllFavorites.sql'),
    getByName: sql('comedians/getByName.sql'),
    getTrending: sql('comedians/getTrending.sql'),
    getAllIdsByUuids: sql('comedians/getAllIdsByUuids.sql')
}

export const favorites = {
    // Create Table
    create: sql('favorites/create.sql'),

    // POST
    add: sql('favorites/add.sql'),

    // DELETE
    remove: sql('favorites/remove.sql')
}

export const groups = {
    // Create Table
    create: sql('groups/comedianGroupCreate.sql'),

    // POST
    add: sql('groups/add.sql'),
}

export const lineups = {
    // Create Table 
    create: sql('lineups/create.sql'),

    getByComedianId: sql('lineups/getByComedianId.sql'),
    getByShowId: sql('lineups/getByShowId.sql')
}

export const search = {
    getHomeSearchResults: sql('search/getHomeSearchResults.sql')
}

export const shows = {
    // Create Table
    create: sql('shows/create.sql'),


    //POST 
    add: sql('shows/add.sql'),

    // GETs
    getAllLineupPopularityData: sql('shows/getAllLineupPopularityData.sql'),
    getWithLineup: sql('shows/getWithLineup.sql'),
    
    //DELETE 

    deleteByClub: sql('shows/deleteByClub.sql')
}

export const tags = {
    // Create Tables
    create: sql('tags/create.sql'),
    createClubTags: sql('tags/createClubTags.sql'),
    createComedianTags: sql('tags/createComedianTags.sql'),
    createShowTags: sql('tags/createShowTags.sql'),
    
    // GET
    getAllByType: sql('tags/getAllByType.sql')
}

export const users = {
    // Create Table
    create: sql('users/create.sql'),

    //POST 
    add: sql('users/add.sql')
}


///////////////////////////////////////////////
// Helper for linking to external query files;
function sql(file: string): pkg.QueryFile {

    const __filename = fileURLToPath(import.meta.url); // get the resolved path to the file
    const __dirname = path.dirname(__filename);
    const fullPath: string = join(__dirname, file); // generating full path;

    const options: IQueryFileOptions = {
        minify: true
    };

    const qf = new pkg.QueryFile(fullPath, options);

    if (qf.error) console.error(qf.error);

    return qf;
}