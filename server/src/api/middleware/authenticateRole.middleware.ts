import { Request, Response, NextFunction } from "express";
import { UserRole } from "../../common/models/@types/UserRole.js";

export const authenticateRole = (roles: UserRole[]) => {
    return (request: Request,
    response: Response,
    next: NextFunction) => {
        if (!roles.includes(request.currentUser.role)) {
            response.status(401);
            return response.send("Not permitted");
          }
        next();
    }
};
