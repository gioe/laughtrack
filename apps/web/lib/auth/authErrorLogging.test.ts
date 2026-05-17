import { describe, expect, it } from "vitest";
import { sanitizeAuthError } from "./authErrorLogging";

describe("sanitizeAuthError", () => {
    it("keeps useful nested error details while redacting sensitive fields", () => {
        const error = new Error("OAuth callback failed");
        error.name = "CallbackRouteError";
        Object.assign(error, {
            type: "Callback",
            code: "Callback",
            clientSecret: "super-secret",
            cause: {
                err: Object.assign(new Error("invalid_client"), {
                    name: "OAuthCallbackError",
                    response: {
                        status: 401,
                        body: {
                            error: "invalid_client",
                            error_description: "Bad client secret",
                            access_token: "access-token",
                            code: "oauth-code",
                        },
                    },
                }),
            },
        });

        expect(sanitizeAuthError(error)).toEqual({
            name: "CallbackRouteError",
            message: "OAuth callback failed",
            type: "Callback",
            code: "Callback",
            cause: {
                err: {
                    name: "OAuthCallbackError",
                    message: "invalid_client",
                    response: {
                        status: 401,
                        body: {
                            error: "invalid_client",
                            error_description: "Bad client secret",
                            access_token: "[redacted]",
                            code: "[redacted]",
                        },
                    },
                },
            },
            clientSecret: "[redacted]",
        });
    });

    it("captures non-enumerable Error.cause details used by Auth.js wrapper errors", () => {
        const rootCause = Object.assign(new Error("invalid_client"), {
            name: "OperationProcessingError",
            response: {
                status: 400,
                body: {
                    error: "invalid_client",
                    error_description: "client authentication failed",
                    id_token: "id-token",
                },
            },
        });
        const error = new Error(
            "Read more at https://errors.authjs.dev#callbackrouteerror",
            {
                cause: {
                    err: rootCause,
                    provider: "apple",
                },
            },
        );
        error.name = "CallbackRouteError";
        Object.assign(error, {
            type: "CallbackRouteError",
            kind: "error",
        });

        expect(sanitizeAuthError(error)).toEqual({
            name: "CallbackRouteError",
            message:
                "Read more at https://errors.authjs.dev#callbackrouteerror",
            cause: {
                err: {
                    name: "OperationProcessingError",
                    message: "invalid_client",
                    response: {
                        status: 400,
                        body: {
                            error: "invalid_client",
                            error_description: "client authentication failed",
                            id_token: "[redacted]",
                        },
                    },
                },
                provider: "apple",
            },
            type: "CallbackRouteError",
            kind: "error",
        });
    });
});
