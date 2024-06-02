import app from "../app.js";
import { Show } from "../types/show.interface.js";
import { scheduleScrapes } from "../util/cron.js";

export const findAll = async (): Promise<Show[]> => {
    return [];
};

export const find = async (id: number): Promise<Show> => {
    return {
        club: {
            name: "",
            website: "",
        },
        dateTime: "",
        name: "",
        comedians: []
    }
};

const server = app.listen(app.get("port"), () => {
    console.log(
        "  App is running at http://localhost:%d in %s mode",
        app.get("port"),
        app.get("env")
    );
    console.log("  Press CTRL-C to stop\n");
    scheduleScrapes();
});

export default server;