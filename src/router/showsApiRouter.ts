import express from "express";
import { getShowsForComic } from "../controllers/showController.js";

export const showsApiRouter = express.Router();

// POST items

showsApiRouter.get("/:name", getShowsForComic)

