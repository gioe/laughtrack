import express, { Request, Response} from "express"; 
import { scrapeAllClubs } from "../controllers/scraper/index.js";

export const scraperApiRouter = express.Router();

// POST items

scraperApiRouter.post("/all", async (req: Request, res: Response) => {
    scrapeAllClubs()
    return res.status(200).send({
        message: 'Running scrapers',
      });
})

