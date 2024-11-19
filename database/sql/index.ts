import { join } from "path";
import pkg from "pg-promise";
import path from "path";
import { fileURLToPath } from "url";
import { createSingleton } from "../../util/singletonUtil";

export const pageDataMap = {
    home: {
        index: sql("home/index.sql").qf
    },
    club: {
        all: {
            index: sql("club/all/index.sql").qf
        },
        slug: {
            index: sql("club/slug/index.sql").qf
        }
    },
    comedian: {
        all: {
            index: sql("comedian/all/index.sql").qf
        },
        slug: {
            index: sql("comedian/slug/index.sql").qf
        }
    },
    show: {
        all: {
            index: sql("show/all/index.sql").qf
        },
        slug: {
            index: sql("show/slug/index.sql").qf
        }
    },
}

export const actionActionMap = {
    club: {
        slug: {
            delete: {
                show: {
                    index: sql("club/slug/delete/index.sql").qf
                }
            }
        }
    },
    comedian: {
        all: {
            index: sql("comedian/all/index.sql").qf
        },
        slug: {
            index: sql("comedian/slug/index.sql").qf
        }
    },
    show: {
        all: {
            index: sql("show/all/index.sql").qf
        },
        slug: {
            index: sql("show/slug/index.sql").qf
        }
    },
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
