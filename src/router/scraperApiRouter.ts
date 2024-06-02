import express from "express";
import { runAllScrapers } from "../controllers/scraperController.js";

export const scraperApiRouter = express.Router();

// POST items

scraperApiRouter.post("/all", runAllScrapers)

