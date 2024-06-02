import express, { Request, Response } from "express";
import * as ComedyService from "./service.js";
import { Item } from "../types/item.interface.js";

export const itemsRouter = express.Router();
  // POST items
  
  itemsRouter.post("/", async (req: Request, res: Response) => {
    try {    
      res.status(201).json();
    } catch (e) {

    }
  });
  