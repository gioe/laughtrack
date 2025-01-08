import { join } from "path";
import pkg from "pg-promise";
import path from "path";
import { fileURLToPath } from "url";
import { createSingleton } from "../../util/singletonUtil";

export const pageDataMap = {
    home: sql("page/home.sql").qf,
    clubSearch: sql("page/clubSearch.sql").qf,
    clubDetail: sql("page/clubDetail.sql").qf,
    editClub: sql("page/editClub.sql").qf,
    comedianSearch: sql("page/comedianSearch.sql").qf,
    comedianDetail: sql("page/comedianDetail.sql").qf,
    editComedian: sql("page/editComedian.sql").qf,
    showSearch: sql("page/showSearch.sql").qf,
    showDetail: sql("page/showDetail.sql").qf,
    profile: sql("page/profile.sql").qf
}

export const apiActionMap = {
    deleteShows: sql("actions/deleteShows.sql").qf,
    addUser: sql("actions/addUser.sql").qf,
    addFavorite: sql("actions/addFavorite.sql").qf,
    addComedian: sql("actions/addComedian.sql").qf,
    updateComedian: sql("actions/updateComedian.sql").qf,
    deleteLineup: sql("actions/deleteLineup.sql").qf,
    deleteFavorite: sql("actions/deleteFavorite.sql").qf,

}

export const queryMap = {
    getAllClubs: sql("queries/getAllClubs.sql").qf,
    getClubById: sql("queries/getClubById.sql").qf,
    getClubByName: sql("queries/getClubByName.sql").qf,
    getClubsByIds: sql("queries/getClubsByIds.sql").qf,
    getComedianIds: sql("queries/getComedianIds.sql").qf,
    getCities: sql("queries/getCities.sql").qf,
    getClubsInCity: sql("queries/getClubsInCity.sql").qf,
    getShowById: sql("queries/getShowById.sql").qf,
    getComediansFromShowMetadata: sql("queries/getComediansFromShowMetadata.sql").qf,
    getTagsFromShowMetadata: sql("queries/getTagsFromShowMetadata.sql").qf,
    getTagsAsFilters: sql("queries/getTagsAsFilters.sql").qf,
    getTrendingComedians: sql("queries/getTrendingComedians.sql").qf
}

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
