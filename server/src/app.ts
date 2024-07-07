import express, { Request, Response, NextFunction } from "express";
import dotenv from "dotenv";
import cors from "cors";
import helmet from "helmet";
import { errorHandler } from "./middleware/error.middleware.js";
import { notFoundHandler } from "./middleware/not-found.middleware.js";
import { showsApiRouter } from "./router/showsApiRouter.js";
import { scraperApiRouter } from "./router/scraperApiRouter.js";
import { comediansApiRouter } from "./router/comediansApiRouter.js";
import { userApiRouter } from "./router/userApiRouter.js";
import { scheduleScrapes } from "./util/types/cron.js";

dotenv.config();

const app = express();

app.set("port", process.env.PORT || 3000);
app.use(helmet());
app.use(cors());
app.use(express.json());

app.use('/api/comedians', comediansApiRouter);
app.use('/api/scraper', scraperApiRouter);
app.use('/api/shows', showsApiRouter);
app.use('/api/user', userApiRouter);

app.use(errorHandler);
app.use(notFoundHandler);

app.listen(app.get("port"), () => {
    console.log(
        "App is running at http://localhost:%d in %s mode",
        app.get("port"),
        app.get("env")
    );
    scheduleScrapes();
});