import { join } from "path";
import pkg from "pg-promise";
import path from "path";
import { fileURLToPath } from "url";
import { createSingleton } from "../../util/singletonUtil";

export const pageDataMap = {
    home: sql("page/home.sql").qf,
    clubSearch: sql("page/clubSearch.sql").qf,
    clubDetail: sql("page/clubDetail.sql").qf,
    comedianSearch: sql("page/comedianSearch.sql").qf,
    comedianDetail: sql("page/comedianDetail.sql").qf,
    showSearch: sql("page/showSearch.sql").qf,
    showDetail: sql("page/showDetail.sql").qf,
}

export const apiActionMap = {
    deleteShows: sql("actions/deleteShows.sql").qf,
    addShow: sql("actions/addShow.sql").qf,
}

export const queryMap = {
    getClubsById: sql("queries/getClubsById.sql").qf,
    getComedianIds: sql("queries/getComedianIds.sql").qf,
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
