import { Request, Response, NextFunction } from "express";
import { UserRole } from "../../@types/UserRole.js";

export const authenticateRole = (role: UserRole) => {
    return (request: Request,
    response: Response,
    next: NextFunction) => {
        if (request.currentUser.role !== role.valueOf()) {
            response.status(401);
            return response.send("Not permitted");
          }
        next();
    }
};
