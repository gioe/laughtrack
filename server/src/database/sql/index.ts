import {  IQueryFileOptions } from 'pg-promise';
import { join } from 'path';
import pkg from 'pg-promise';
import path from 'path';
import { fileURLToPath } from 'url';


export const clubs = {
    add: sql('clubs/add.sql'),
    allPopularityData: sql('clubs/allPopularityData.sql'),
    create: sql('clubs/create.sql'),
    delete: sql('clubs/delete.sql'),
    drop: sql('clubs/drop.sql'),
    empty: sql('clubs/empty.sql'),
    getCities: sql('clubs/getCities.sql'),
    getDetails: sql('clubs/getDetails.sql'),
    getTrending: sql('clubs/getTrending.sql'),
    getWithSchedule: sql('clubs/getWithSchedule.sql')
}

export const comedians = {
    add: sql('comedians/add.sql'),
    allPopularityData: sql('comedians/allPopularityData.sql'),
    create: sql('comedians/create.sql'),
    drop: sql('comedians/drop.sql'),
    empty: sql('comedians/empty.sql'),
    getTrending: sql('comedians/getTrending.sql'),
    getDetails: sql('comedians/getDetails.sql'),
    updateScores: sql('comedians/updateScores.sql')
}

export const shows = {
    add: sql('shows/add.sql'),
    allPopularityData: sql('shows/allPopularityData.sql'),
    create: sql('shows/create.sql'),
    drop: sql('shows/drop.sql'),
    empty: sql('shows/empty.sql'),
    getWithLineup: sql('shows/getWithLineup.sql'),
    getSearchResults: sql('shows/getSearchResults.sql')
}

export const users = {
    add: sql('users/add.sql'),
    create: sql('users/create.sql'),
    drop: sql('users/drop.sql'),
    empty: sql('users/empty.sql'),
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