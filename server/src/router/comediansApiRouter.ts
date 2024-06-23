import express from "express";
import { getAllComedians, getShowsForComedian } from "../controllers/comediansController.js";

export const comediansApiRouter = express.Router();

// POST items

comediansApiRouter.get("/all", getAllComedians)
comediansApiRouter.get("/", getShowsForComedian)

