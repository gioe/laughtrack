export default class HttpException extends Error {
    statusCode?: number;
    status?: number;
    message: string;
    error: string | null;

    constructor(statusCode: number, message: string, error?: string) {
        super(message);
        Object.setPrototypeOf(this, new.target.prototype);

        this.statusCode = statusCode;
        this.message = message;
        this.error = error || null;
    }
}
