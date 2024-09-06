import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import * as userController from '../controllers/user/index.js'
import { AuthToken } from "../interfaces/token.interface..js";

export const assignUser = async (
    request: Request,
    response: Response,
    next: NextFunction
  ) => {
    const token = request.header('Authorization');
    if (!token) return response.status(401).json({ error: 'Access denied' });
    try {
        const decoded = jwt.verify(token, process.env.SECRET_KEY as string) as AuthToken;
        const user = await userController.getUserByEmail(decoded.email)
        request.currentUser = user;
        next();
    } catch (error) {
        response.status(401).json({ error: 'Invalid token' });
    }
};


