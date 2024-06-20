import express from "express";
import { getAllComedians, getTrendingComedians } from "../controllers/comediansController.js";

export const comediansApiRouter = express.Router();

// POST items

comediansApiRouter.get("/all", getAllComedians)
comediansApiRouter.get("/trending", getTrendingComedians)

