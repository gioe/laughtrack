import express, { Application } from "express";
import pkg from 'pg';
const { Pool } = pkg;
import cors from "cors";
import helmet from "helmet";
import { privateComediansApiRouter, publicComediansApiRouter } from "./api/routes/comedians.js";
import { privateShowsApiRouter, publicShowsApiRouter } from "./api/routes/shows.js";
import { authApiRouter } from "./api/routes/auth.js";
import { errorHandler } from "./api/middleware/error.middleware.js";
import { notFoundHandler } from "./api/middleware/not-found.middleware.js";
import { privateClubsApiRouter, publicClubsApiRouter } from "./api/routes/clubs.js";
import { healthCheckApiRouter } from "./api/routes/healthcheck.js";
import {
    generateRemoteDBConnection,
    generateLocalDBConnection
} from "./database/config.js";
import { isLocal } from "./api/util/environmentUtil.js";
import { downloadBucketContents } from "./api/util/cloudStorageUtil.js";


class App {
    public app: Application;

    constructor() {
        this.app = express()
        this.publicRoutes()
        // this.privateRoutes()
        this.middleLayers()
        this.setupCache()
        this.setupDb()
    }

    protected setupCache(): void {
        if (isLocal) downloadBucketContents()
    }

    protected setupDb(): void {
        if (isLocal) generateLocalDBConnection()
        else generateRemoteDBConnection()
    }

    protected generateCachedFiles(): void {
        downloadBucketContents()
    }

    protected publicRoutes(): void {
        this.app.use('/auth', authApiRouter);
        this.app.use('/comedians', privateComediansApiRouter);
        this.app.use('/comedians', publicComediansApiRouter);
        this.app.use('/clubs', privateClubsApiRouter);
        this.app.use('/clubs', publicClubsApiRouter);
        this.app.use('/shows', privateShowsApiRouter);
        this.app.use('/shows', publicShowsApiRouter);
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
