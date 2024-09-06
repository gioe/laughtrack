import express, { Request, Response} from "express"; 
import * as scraperController from "../controllers/scraper/index.js"
import { assignUser } from "../middleware/assignUser.middleware.js";
import { authenticateRole } from "../middleware/authenticateRole.middleware.js";
import { UserRole } from "../../@types/UserRole.js";

export const scraperApiRouter = express.Router();
scraperApiRouter.use(assignUser)
scraperApiRouter.use(authenticateRole(UserRole.Admin))

scraperApiRouter.post("/all",
  async (req: Request, res: Response) => {
    scraperController.scrapeAllClubs()
    return res.status(200).send({
        message: 'Running scrapers',
    });
})

scraperApiRouter.post('/:id',
  async (req: Request, res: Response) => {
  
  const id = Number(req.params.id)

  scraperController.scrapeClub(id)

  return res.status(200).send({
      message: 'Running scrapers',
    });
})
