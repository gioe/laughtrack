import express, { Request, Response} from "express"; 
import * as scraperController from "../controllers/scraper/index.js"
import { verifyToken } from "../middleware/auth.middleware.js";

export const scraperApiRouter = express.Router();

scraperApiRouter.post("/all", verifyToken, async (req: Request, res: Response) => {
    scraperController.scrapeAllClubs()
    return res.status(200).send({
        message: 'Running scrapers',
      });
})

scraperApiRouter.post('/:id', verifyToken, async (req: Request, res: Response) => {
  
  const id = Number(req.params.id)

  scraperController.scrapeClub(id)

  return res.status(200).send({
      message: 'Running scrapers',
    });
})
