import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";

export const verifyToken = (
    request: Request,
    response: Response,
    next: NextFunction
  ) => {
    console.log(request)
    const token = request.header('Authorization');
    if (!token) return response.status(401).json({ error: 'Access denied' });
    try {
        const decoded = jwt.verify(token, process.env.SECRET_KEY as string);
        next();
    } catch (error) {
        response.status(401).json({ error: 'Invalid token' });
    }
};
