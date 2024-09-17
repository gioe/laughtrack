import express, { Application } from "express";
import pkg from 'pg';
const { Pool } = pkg;
import cors from "cors";
import helmet from "helmet";
import { comediansApiRouter } from "./api/routes/api/comedians.js";
import { showsApiRouter } from "./api/routes/api/shows.js";
import { authApiRouter } from "./api/routes/auth.js";
import { errorHandler } from "./api/middleware/error.middleware.js";
import { notFoundHandler } from "./api/middleware/not-found.middleware.js";
import { clubsApiRouter } from "./api/routes/api/clubs.js";
import {
    generateRemoteDBConnection,
    generateLocalDBConnection
} from "./database/config.js";
import { isLocal } from "./api/util/environmentUtil.js";
import { downloadBucketContents } from "./api/util/cloudStorageUtil.js";
import { comediansAdminRouter } from "./api/routes/admin/comedians.js";
import { healthCheckApiRouter } from "./api/routes/admin/healthcheck.js";
import { clubsAdminRouter } from "./api/routes/admin/clubs.js";
import { showsAdminRouter } from "./api/routes/admin/shows.js";

class App {
    public app: Application;

    constructor() {
        this.app = express()
        this.adminRoutes()
        this.apiRoutes()
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

    protected apiRoutes(): void {
        this.app.use('/auth', authApiRouter);
        this.app.use('/api/comedians', comediansApiRouter);
        this.app.use('/api/clubs', clubsApiRouter);
        this.app.use('/api/shows', showsApiRouter);
    }

    protected adminRoutes(): void {
        this.app.use('/admin/comedian', comediansAdminRouter)
        this.app.use('/admin/clubs', clubsAdminRouter);
        this.app.use('/admin/shows', showsAdminRouter);
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
