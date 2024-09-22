import express, { Application } from "express";
import pkg from 'pg';
const { Pool } = pkg;
import cors from "cors";
import helmet from "helmet";
import { comedianApiRouter } from "./api/routes/api/comedian.js";
import { showApiRouter } from "./api/routes/api/show.js";
import { authApiRouter } from "./api/routes/auth.js";
import { errorHandler } from "./api/middleware/error.middleware.js";
import { notFoundHandler } from "./api/middleware/not-found.middleware.js";
import { clubApiRouter } from "./api/routes/api/club.js";
import {
    generateRemoteDBConnection,
    generateLocalDBConnection
} from "./database/config.js";
import { isLocal } from "./api/util/environmentUtil.js";
import { downloadBucketContents } from "./api/util/cloudStorageUtil.js";
import { comedianAdminRouter } from "./api/routes/admin/comedian.js";
import { healthCheckApiRouter } from "./api/routes/admin/healthcheck.js";
import { clubAdminRouter } from "./api/routes/admin/club.js";
import { showAdminRouter } from "./api/routes/admin/show.js";

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
        this.app.use('/api/comedian', comedianApiRouter);
        this.app.use('/api/club', clubApiRouter);
        this.app.use('/api/show', showApiRouter);
    }

    protected adminRoutes(): void {
        this.app.use('/admin/comedian', comedianAdminRouter)
        this.app.use('/admin/club', clubAdminRouter);
        this.app.use('/admin/show', showAdminRouter);
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
