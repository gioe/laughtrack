import express, { Application } from "express";
import cors from "cors";
import helmet from "helmet";
import cookieParser from 'cookie-parser';
import { comedianApiRouter } from "./api/routes/api/comedian.js";
import { showApiRouter } from "./api/routes/api/show.js";
import { authApiRouter } from "./api/routes/api/auth.js";
import { errorHandler } from "./api/middleware/error.middleware.js";
import { notFoundHandler } from "./api/middleware/not-found.middleware.js";
import { clubApiRouter } from "./api/routes/api/club.js";
import { isLocal } from "./common/util/environmentUtil.js";
import { downloadBucketContents } from "./common/util/cloudStorageUtil.js";
import { searchApiRouter } from "./api/routes/api/search.js";

class App {
    public app: Application;

    constructor() {
        this.app = express()
        this.apiRoutes()
        this.middleLayers()
        this.setupCache()
    }

    protected setupCache(): void {
        if (isLocal) downloadBucketContents()
    }

    protected generateCachedFiles(): void {
        downloadBucketContents()
    }

    protected apiRoutes(): void {
        this.app.use('/auth', authApiRouter);
        this.app.use('/api/comedian', comedianApiRouter);
        this.app.use('/api/club', clubApiRouter);
        this.app.use('/api/show', showApiRouter);
        this.app.use('/api/search', searchApiRouter);
    }

    protected middleLayers(): void {
        this.app.use(errorHandler);
        this.app.use(notFoundHandler);
        this.app.use(helmet());
        this.app.use(cors());
        this.app.use(express.json());
        this.app.use(cookieParser());
    }
    
}

const app = new App().app;

app.listen(process.env.PORT, () => {
    console.log(`App is running at http://localhost:${process.env.PORT}`);
});
