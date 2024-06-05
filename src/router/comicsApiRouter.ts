import express from "express";
import { getAllComics } from "../controllers/comicsController.js";

export const comicsApiRouter = express.Router();

// POST items

comicsApiRouter.get("/blah", getAllComics)

