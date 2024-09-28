import {  IQueryFileOptions } from 'pg-promise';
import { join } from 'path';
import pkg from 'pg-promise';
import path from 'path';
import { fileURLToPath } from 'url';

///////////////////////////////////////////////////////////////////////////////////////////////
// Criteria for deciding whether to place a particular query into an external SQL file or to
// keep it in-line (hard-coded):
//
// - Size / complexity of the query, because having it in a separate file will let you develop
//   the query and see the immediate updates without having to restart your application.
//
// - The necessity to document your query, and possibly keeping its multiple versions commented
//   out in the query file.
//
// In fact, the only reason one might want to keep a query in-line within the code is to be able
// to easily see the relation between the query logic and its formatting parameters. However, this
// is very easy to overcome by using only Named Parameters for your query formatting.
////////////////////////////////////////////////////////////////////////////////////////////////

export const cities = {
    add: sql('cities/add.sql'),
    create: sql('cities/create.sql'),
    drop: sql('cities/drop.sql'),
    empty: sql('cities/empty.sql')
}

export const clubs = {
    add: sql('clubs/add.sql'),
    create: sql('clubs/create.sql'),
    delete: sql('clubs/delete.sql'),
    drop: sql('clubs/drop.sql'),
    empty: sql('clubs/empty.sql'),
    getTrending: sql('clubs/getTrending.sql'),
    getWithSchedule: sql('clubs/getWithSchedule.sql')
}

export const comedians = {
    add: sql('comedians/add.sql'),
    create: sql('comedians/create.sql'),
    drop: sql('comedians/drop.sql'),
    empty: sql('comedians/empty.sql'),
    getTrending: sql('comedians/getTrending.sql')
}

export const showComedians = {
    add: sql('showComedians/add.sql'),
    create: sql('showComedians/create.sql'),
    drop: sql('showComedians/drop.sql'),
    empty: sql('showComedians/empty.sql')
}

export const shows = {
    add: sql('shows/add.sql'),
    create: sql('shows/create.sql'),
    drop: sql('shows/drop.sql'),
    empty: sql('shows/empty.sql')
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

        // minifying the SQL is always advised;
        // see also option 'compress' in the API;
        minify: true

        // See also property 'params' for two-step template formatting
    };

    const qf = new pkg.QueryFile(fullPath, options);

    if (qf.error) {
        // Something is wrong with our query file :(
        // Testing all files through queries can be cumbersome,
        // so we also report it here, while loading the module:
        console.error(qf.error);
    }

    return qf;

    // See QueryFile API:
    // http://vitaly-t.github.io/pg-promise/QueryFile.html
}