import express, { Request, Response} from "express"; 
import * as scraperController from "../controllers/scraper/index.js"
import { authenticateRole, verifyToken } from "../middleware/auth.middleware.js";
import { UserRole } from "../../types/UserRole.js";

export const scraperApiRouter = express.Router();

scraperApiRouter.post("/all",
  verifyToken, 
  authenticateRole(UserRole.Admin), 
  async (req: Request, res: Response) => {
    scraperController.scrapeAllClubs()
    return res.status(200).send({
        message: 'Running scrapers',
    });
})

scraperApiRouter.post('/:id', 
  verifyToken, 
  authenticateRole(UserRole.Admin), 
  async (req: Request, res: Response) => {
  
  const id = Number(req.params.id)

  scraperController.scrapeClub(id)

  return res.status(200).send({
      message: 'Running scrapers',
    });
})
