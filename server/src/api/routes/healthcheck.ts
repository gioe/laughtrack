import express, { Request, Response} from "express"; 
import { getUser } from "../controllers/user/userController.js";

export const healthCheckApiRouter = express.Router();

// POST items

healthCheckApiRouter.get("/", async (req: Request, res: Response) => {
   
    const healthCheck = {
        uptime: process.uptime(),
        responsetime: process.hrtime(),
        message: 'OK',
        timestampe: Date.now(),
    }
   
    try {
        res.send(healthCheck)
    } catch (e) {
        res.status(503).send();
    }
    
})