import express, { Request, Response} from "express"; 
import * as scraperController from "../controllers/scraper/index.js"

export const scraperApiRouter = express.Router();

scraperApiRouter.post("/all", async (req: Request, res: Response) => {
    scraperController.scrapeAllClubs()
    return res.status(200).send({
        message: 'Running scrapers',
      });
})

scraperApiRouter.post('/:id', async (req: Request, res: Response) => {
  
  const id = String(req.params.id)
  console.log(id)
  scraperController.scrapeClub(id)

  return res.status(200).send({
      message: 'Running scrapers',
    });
})
