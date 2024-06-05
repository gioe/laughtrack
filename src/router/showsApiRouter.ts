import express from "express";
import { getShowsForBlah } from "../controllers/showController.js";

export const showsApiRouter = express.Router();

// POST items

showsApiRouter.get("/blah", getShowsForBlah)

