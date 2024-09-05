import express, { Application } from "express";
import cors from "cors";
import helmet from "helmet";
import { scheduleScrapes } from "./util/cronUtil.js";
import { comediansApiRouter } from "./api/routes/comedians.js";
import { scraperApiRouter } from "./api/routes/scraper.js";
import { showsApiRouter } from "./api/routes/shows.js";
import { userApiRouter } from "./api/routes/user.js";
import { errorHandler } from "./api/middleware/error.middleware.js";
import { notFoundHandler } from "./api/middleware/not-found.middleware.js";
import { clubsApiRouter } from "./api/routes/clubs.js";
import { createClubsTable, createComediansTable, createShowsTable, createShowComediansTable } from "./database/config.js";

class App {
    public app: Application;

    constructor() {
        this.app = express()
        this.app.set("port", process.env.PORT || 3000);
        this.routes()
        this.middleLayers()
        this.databaseSync()
    }

    protected databaseSync(): void {
        createClubsTable()
        .then(() => createShowsTable())
        .then(() => createComediansTable())
        .then(() => createShowComediansTable())
    }

    protected routes(): void {
        this.app.use('/comedians', comediansApiRouter);
        this.app.use('/scraper', scraperApiRouter);
        this.app.use('/shows', showsApiRouter);
        this.app.use('/user', userApiRouter);
        this.app.use('/clubs', clubsApiRouter);
    }

    protected middleLayers(): void {
        this.app.use(errorHandler);
        this.app.use(notFoundHandler);
        this.app.use(helmet());
        this.app.use(cors());
        this.app.use(express.json());
 }
}

const app = new App().app;

app.listen(app.get("port"), () => {
    console.log(
        "App is running at http://localhost:%d in %s mode",
        app.get("port"),
        app.get("env")
    );
    scheduleScrapes();
});
