import express, { Application } from "express";
import pkg from 'pg';
const { Pool } = pkg;
import cors from "cors";
import helmet from "helmet";
import { comediansApiRouter } from "./api/routes/comedians.js";
import { scraperApiRouter } from "./api/routes/scraper.js";
import { showsApiRouter } from "./api/routes/shows.js";
import { userApiRouter } from "./api/routes/user.js";
import { errorHandler } from "./api/middleware/error.middleware.js";
import { notFoundHandler } from "./api/middleware/not-found.middleware.js";
import { clubsApiRouter } from "./api/routes/clubs.js";
import { healthCheckApiRouter } from "./api/routes/healthcheck.js";
import {
    createClubsTable, 
    createComediansTable, 
    createShowsTable, 
    createShowComediansTable, 
    createUsersTable, 
    generateDBConnectionPool
} from "./database/config.js";
import { isLocal } from "./util/environmentUtil.js";
import { downloadBucketContents } from "./util/cloudStorageUtil.js";


class App {
    public app: Application;

    constructor() {
        this.app = express()
        this.routes()
        this.middleLayers()
        this.setupDb()
        if (isLocal) {
            this.generateCachedFiles()
        }
    }

    protected setupDb(): void {
        generateDBConnectionPool()
        .then((pool: pkg.Pool) => this.generateTables(pool))
    }

    protected generateTables = async (pool: pkg.Pool) => {
        return createClubsTable(pool)
        .then(() => createShowsTable(pool))
        .then(() => createComediansTable(pool))
        .then(() => createShowComediansTable(pool))
        .then(() => createUsersTable(pool));
    }

    protected generateCachedFiles(): void {
        downloadBucketContents()
    }

    protected routes(): void {
        this.app.use('/comedians', comediansApiRouter);
        this.app.use('/scraper', scraperApiRouter);
        this.app.use('/shows', showsApiRouter);
        this.app.use('/user', userApiRouter);
        this.app.use('/clubs', clubsApiRouter);
        this.app.use('/healthcheck', healthCheckApiRouter);
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

app.listen(process.env.PORT, () => {
    console.log(`App is running at http://localhost:${process.env.PORT}`);
});
