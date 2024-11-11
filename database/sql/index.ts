import { join } from "path";
import pkg from "pg-promise";
import path from "path";
import { fileURLToPath } from "url";
import { createSingleton } from "../../util/singletonUtil";
import { QueryFileMap } from "../../objects/types/queryFileMap";

export const city = {
    // Create Table
    createTable: sql("city/createTable.sql").qf,

    // GETs
    getAll: sql("city/get/all.sql").qf


} as QueryFileMap;

export const club = {
    // Create Table
    createTable: sql("club/createTable.sql").qf,

    // ASC GETs
    allByNameAsc: sql("club/get/asc/allByNameAsc.sql").qf,
    allByPopularityAsc: sql("club/get/asc/allByPopularityAsc.sql").qf,

    // DESC GETs
    allByNameDesc: sql("club/get/desc/allByNameDesc.sql").qf,
    allByPopularityDesc: sql("club/get/desc/allByPopularityDesc.sql").qf,

    // GETs
    getByName: sql("club/get/name.sql").qf,
    getById: sql("club/get/id.sql").qf,
    getByCity: sql("club/get/city.sql").qf

} as QueryFileMap;

export const comedian = {
    // Create Table
    createTable: sql("comedian/createTable.sql").qf,

    // ASC GETs
    allByNameAsc: sql("comedian/get/asc/allByNameAsc.sql").qf,
    allByPopularityAsc: sql("comedian/get/asc/allByPopularityAsc.sql").qf,

    // DESC GETs
    allByNameDesc: sql("comedian/get/desc/allByNameDesc.sql").qf,
    allByPopularityDesc: sql("comedian/get/desc/allByPopularityDesc.sql").qf,

    // GETs
    getByName: sql("comedian/get/name.sql").qf,
    getById: sql("comedian/get/id.sql").qf,
    getTrending: sql("comedian/get/trending.sql").qf,

} as QueryFileMap;

export const favorite = {
    // Create Table
    createTable: sql("favorite/createTable.sql").qf,

    // POST
    add: sql("favorite/add.sql").qf,

    // DELETE
    remove: sql("favorite/remove.sql").qf,
} as QueryFileMap;

export const lineupItem = {
    // Create Table
    createTable: sql("lineupItem/createTable.sql").qf,
    getByComedianId: sql("lineupItem/get/comedianId.sql").qf,
    getByShowId: sql("lineupItem/get/showId.sql").qf,
} as QueryFileMap;

export const show = {
    // Create Table
    createTable: sql("show/createTable.sql").qf,

    //POST
    add: sql("show/add.sql").qf,

    // ASC GETs
    allByScapeDateAsc: sql("show/get/asc/allByScapeDateAsc.sql").qf,
    allByDateAsc: sql("show/get/asc/allByDateAsc.sql").qf,
    allByNameAsc: sql("show/get/asc/allByNameAsc.sql").qf,
    allByPopularityAsc: sql("show/get/asc/allByPopularityAsc.sql").qf,
    allByPriceAsc: sql("show/get/asc/allByPriceAsc.sql").qf,

    // DESC GETs
    allByScrapeDateDesc: sql("show/get/desc/allByScrapeDateDesc.sql").qf,
    allByDateDesc: sql("show/get/desc/allByDateDesc.sql").qf,
    allByNameDesc: sql("show/get/desc/allByNameDesc.sql").qf,
    allByPopularityDesc: sql("show/get/desc/allByPopularityDesc.sql").qf,
    allByPriceDesc: sql("show/get/desc/allByPriceDesc.sql").qf,

    // Property GETs
    getById: sql("show/get/id.sql").qf,
    getByName: sql("show/get/name.sql").qf,

    //DELETE
    deleteByClub: sql("show/delete/club.sql").qf,
} as QueryFileMap;

export const tag = {
    // Create Tables
    createTable: sql("tag/createTable.sql").qf,
    createTaggedClubsTable: sql("tag/createTaggedClubsTable.sql").qf,
    createTaggedComediansTable: sql("tag/createTaggedComediansTable.sql").qf,
    createTaggedShowsTable: sql("tag/createTaggedShowsTable.sql").qf,

    // GET
    getByType: sql("tag/get/type.sql").qf,
} as QueryFileMap;

export const user = {
    // Create Table
    createTable: sql("user/createTable.sql").qf,

    //POST
    add: sql("user/add.sql").qf,
} as QueryFileMap;

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
