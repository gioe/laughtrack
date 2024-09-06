import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { UserRole } from "../../types/UserRole.js";

export const verifyToken = (
    request: Request,
    response: Response,
    next: NextFunction
  ) => {

    const token = request.header('Authorization');
    if (!token) return response.status(401).json({ error: 'Access denied' });
    try {
        const decoded = jwt.verify(token, process.env.SECRET_KEY as string);
        next();
    } catch (error) {
        response.status(401).json({ error: 'Invalid token' });
    }
};

export const authenticateRole = (role: UserRole) => {
    return (request: Request,
    response: Response,
    next: NextFunction) => {
        if (true) {
            response.status(401);
            return response.send("Not permitted");
          }
          next();
    }
};
