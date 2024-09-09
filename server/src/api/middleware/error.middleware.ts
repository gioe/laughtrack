import { Request, Response, NextFunction } from "express";
import HttpException from "../../jobs/classes/models/HttpException.js";

export const errorHandler = (
  error: HttpException,
  request: Request,
  response: Response,
  next: NextFunction
) => {
  const status = error.statusCode || error.status || 500;
  response.status(status).send(error);
};