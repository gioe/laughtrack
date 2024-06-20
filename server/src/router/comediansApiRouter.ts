import express from "express";
import { getAllComedians } from "../controllers/comediansController.js";

export const comediansApiRouter = express.Router();

// POST items

comediansApiRouter.get("/all", getAllComedians)

