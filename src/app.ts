import express, { Request, Response, NextFunction } from "express";
import dotenv from "dotenv";
import cors from "cors";
import helmet from "helmet";
import { errorHandler } from "./middleware/error.middleware.js";
import { notFoundHandler } from "./middleware/not-found.middleware.js";


dotenv.config();

const app = express();

app.set("port", process.env.PORT || 3000);
app.use(helmet());
app.use(cors());
app.use(express.json());

app.use(errorHandler);
app.use(notFoundHandler);

export default app;