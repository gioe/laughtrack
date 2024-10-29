import winston from 'winston'
const { combine, timestamp, json } = winston.format;

const dateString = new Date().toDateString().replaceAll(" ", "_")

const infoLogger = winston.createLogger({
  level: 'info',
  format: combine(timestamp(), json()),
  transports: [
    new winston.transports.File({
      filename: `logs/${dateString}.log`,
    }),
    new winston.transports.Console()
  ],
});

const errorLogger = winston.createLogger({
  level: 'error',
  format: combine(timestamp(), json()),
  transports: [
    new winston.transports.File({
      filename: `logs/${dateString}.log`,
    }),
    new winston.transports.Console() 
  ],
});

export const writeLogToFile = (string: string) => {
  infoLogger.info(string);
}

export const writeFailureToFile = (string: string) => {
  errorLogger.error(string);
}
 