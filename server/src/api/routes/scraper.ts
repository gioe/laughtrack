import express from "express";
import { runAllScrapers } from "../controllers/scraper/scraperController.js";

export const scraperApiRouter = express.Router();

// POST items

scraperApiRouter.post("/all", runAllScrapers)

