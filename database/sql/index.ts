import { join } from "path";
import pkg from "pg-promise";
import path from "path";
import { fileURLToPath } from "url";
import { createSingleton } from "../../util/singletonUtil";


export const city = {
    // Create Table
    createTable: sql("city/createTable.sql").qf,

    // GETs
    getAll: sql("city/get/all.sql").qf


};

export const club = {
    // Create Table
    createTable: sql("club/createTable.sql").qf,

    // GETs
    getByName: sql("club/get/name.sql").qf,
    getById: sql("club/get/id.sql").qf,
    getAll: sql("club/get/all.sql").qf,
    getByCity: sql("club/get/city.sql").qf

};

export const comedian = {
    // Create Table
    createTable: sql("comedian/createTable.sql").qf,

    // GETs
    getAll: sql("comedian/get/all.sql").qf,
    getByName: sql("comedian/get/name.sql").qf,
    getById: sql("comedian/get/id.sql").qf,
    getTrending: sql("comedian/get/trending.sql").qf,
};


export const favorite = {
    // Create Table
    createTable: sql("favorite/createTable.sql").qf,

    // POST
    add: sql("favorite/add.sql").qf,

    // DELETE
    remove: sql("favorite/remove.sql").qf,
};


export const lineupItem = {
    // Create Table
    createTable: sql("lineupItem/createTable.sql").qf,
    getByComedianId: sql("lineupItem/get/comedianId.sql").qf,
    getByShowId: sql("lineupItem/get/showId.sql").qf,
};

export const show = {
    // Create Table
    createTable: sql("show/createTable.sql").qf,

    //POST
    add: sql("show/add.sql").qf,

    // GETs
    getAll: sql("show/get/all.sql").qf,
    getById: sql("show/get/id.sql").qf,
    getByName: sql("show/get/name.sql").qf,

    //DELETE
    deleteByClub: sql("show/delete/club.sql").qf,
};

export const tag = {
    // Create Tables
    createTable: sql("tag/createTable.sql").qf,
    createTaggedClubsTable: sql("tag/createTaggedClubsTable.sql").qf,
    createTaggedComediansTable: sql("tag/createTaggedComediansTable.sql").qf,
    createTaggedShowsTable: sql("tag/createTaggedShowsTable.sql").qf,

    // GET
    getByType: sql("tag/get/type.sql").qf,
};

export const user = {
    // Create Table
    createTable: sql("user/createTable.sql").qf,

    //POST
    add: sql("user/add.sql").qf,
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
