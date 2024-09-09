import express, { Request, Response} from "express"; 
import { assignUser } from "../middleware/assignUser.middleware.js";
import { authenticateRole } from "../middleware/authenticateRole.middleware.js";
import { UserRole } from "../@types/UserRole.js";

export const healthCheckApiRouter = express.Router();
healthCheckApiRouter.use(assignUser)
healthCheckApiRouter.use(authenticateRole(UserRole.Admin))
// POST items

healthCheckApiRouter.get("/", 
    async (req: Request, res: Response) => {
   
    const healthCheck = {
        uptime: process.uptime(),
        responsetime: process.hrtime(),
        message: 'OK',
        timestamp: Date.now(),
    }
   
    try {
        res.send(healthCheck)
    } catch (e) {
        res.status(503).send();
    }
    
})