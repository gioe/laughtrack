import app from "./app.js";
import { scheduleScrapes } from "./util/cron.js";

/**
 * Start Express server.
 */
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