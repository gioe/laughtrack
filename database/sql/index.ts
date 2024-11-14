import { join } from "path";
import pkg from "pg-promise";
import path from "path";
import { fileURLToPath } from "url";
import { createSingleton } from "../../util/singletonUtil";
import { QueryFileMap } from "../../objects/type/queryFileMap";

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
    getAllByNameAsc: sql("club/get/all/asc/getAllByNameAsc.sql").qf,
    getAllByPopularityAsc: sql("club/get/all/asc/getAllByPopularityAsc.sql").qf,
    getIdByDateAsc: sql("club/get/id/asc/getIdByDateAsc.sql").qf,
    getIdByPopularityAsc: sql("club/get/id/asc/getIdByPopularityAsc.sql").qf,
    getNameByDateAsc: sql("club/get/name/asc/getNameByDateAsc.sql").qf,
    getNameByPopularityAsc: sql("club/get/name/asc/getNameByPopularityAsc.sql").qf,
    // DESC GETs
    getAllByNameDesc: sql("club/get/all/desc/getAllByNameDesc.sql").qf,
    getAllByPopularityDesc: sql("club/get/all/desc/getAllByPopularityDesc.sql").qf,
    getIdByDateDesc: sql("club/get/id/desc/getIdByDateDesc.sql").qf,
    getIdByPopularityDesc: sql("club/get/id/desc/getIdByPopularityDesc.sql").qf,
    getNameByDateDesc: sql("club/get/name/desc/getNameByDateDesc.sql").qf,
    getNameByPopularityDesc: sql("club/get/name/desc/getNameByPopularityDesc.sql").qf,

    // GETs
    getByCity: sql("club/get/city/getByCity.sql").qf
} as QueryFileMap;

export const comedian = {
    // Create Table
    createTable: sql("comedian/createTable.sql").qf,

    // ASC GETs
    getAllByNameAsc: sql("comedian/get/all/asc/getAllByNameAsc.sql").qf,
    getAllByPopularityAsc: sql("comedian/get/all/asc/getAllByPopularityAsc.sql").qf,

    // DESC GETs
    getAllByNameDesc: sql("comedian/get/all/desc/getAllByNameDesc.sql").qf,
    getAllByPopularityDesc: sql("comedian/get/all/desc/getAllByPopularityDesc.sql").qf,

    // GETs
    getById: sql("comedian/get/id/asc/getAllByDateAsc.sql").qf,
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
    getAllByScapeDateAsc: sql("show/get/all/asc/getAllByScapeDateAsc.sql").qf,
    getAllByDateAsc: sql("show/get/all/asc/getAllByDateAsc.sql").qf,
    getAllByNameAsc: sql("show/get/all/asc/getAllByNameAsc.sql").qf,
    getAllByPopularityAsc: sql("show/get/all/asc/getAllByPopularityAsc.sql").qf,
    getAllByPriceAsc: sql("show/get/all/asc/getAllByPriceAsc.sql").qf,

    // DESC GETs
    getAllByScrapeDateDesc: sql("show/get/all/desc/getAllByScrapeDateDesc.sql").qf,
    getAllByDateDesc: sql("show/get/all/desc/getAllByDateDesc.sql").qf,
    getAllByNameDesc: sql("show/get/all/desc/getAllByNameDesc.sql").qf,
    getAllByPopularityDesc: sql("show/get/all/desc/getAllByPopularityDesc.sql").qf,
    getAllByPriceDesc: sql("show/get/all/desc/getAllByPriceDesc.sql").qf,

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

    // GET
    getByEmail: sql("user/get/getByEmail.sql").qf,
    getById: sql("user/get/getById.sql").qf,
    getAll: sql("user/get/getAll.sql").qf,

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
