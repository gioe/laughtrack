import express from "express";
import { runAllScrapers, scrapeClub } from "../controllers/scraperController.js";

export const scraperApiRouter = express.Router();

// POST items

scraperApiRouter.post("/all", runAllScrapers)
scraperApiRouter.post("/", scrapeClub)


