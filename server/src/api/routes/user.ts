import express from "express";
import { getUser } from "../controllers/user/userController.js";

export const userApiRouter = express.Router();

// POST items

userApiRouter.get("/all", getUser)

