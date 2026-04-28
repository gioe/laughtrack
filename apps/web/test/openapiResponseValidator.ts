import openApiSpec from "../../../ios/Sources/LaughTrackAPIClient/openapi.json";

type JsonSchema = {
    $ref?: string;
    type?: string | string[];
    required?: string[];
    properties?: Record<string, JsonSchema>;
    items?: JsonSchema;
};

type OpenApiSpec = {
    paths: Record<
        string,
        {
            get?: {
                responses?: Record<
                    string,
                    {
                        content?: {
                            "application/json"?: {
                                schema?: JsonSchema;
                            };
                        };
                    }
                >;
            };
        }
    >;
    components: {
        schemas: Record<string, JsonSchema>;
    };
};

const spec = openApiSpec as OpenApiSpec;

function resolveRef(ref: string): JsonSchema {
    const prefix = "#/components/schemas/";
    if (!ref.startsWith(prefix)) {
        throw new Error(`Unsupported OpenAPI ref: ${ref}`);
    }

    const schemaName = ref.slice(prefix.length);
    const schema = spec.components.schemas[schemaName];
    if (!schema) {
        throw new Error(`Missing OpenAPI schema: ${schemaName}`);
    }

    return schema;
}

function validateType(value: unknown, type: string): boolean {
    if (type === "null") return value === null;
    if (type === "array") return Array.isArray(value);
    if (type === "integer") return Number.isInteger(value);
    if (type === "number") return typeof value === "number";
    if (type === "object") {
        return (
            typeof value === "object" && value !== null && !Array.isArray(value)
        );
    }
    return typeof value === type;
}

function schemaHasType(schema: JsonSchema, type: string): boolean {
    if (!schema.type) return false;
    return Array.isArray(schema.type)
        ? schema.type.includes(type)
        : schema.type === type;
}

function validateSchema(
    value: unknown,
    schema: JsonSchema,
    path: string,
): string[] {
    const resolved = schema.$ref ? resolveRef(schema.$ref) : schema;
    const errors: string[] = [];

    if (resolved.type) {
        const types = Array.isArray(resolved.type)
            ? resolved.type
            : [resolved.type];
        if (!types.some((type) => validateType(value, type))) {
            errors.push(`${path} expected ${types.join(" or ")}`);
            return errors;
        }
    }

    if (value === null) return errors;

    if (
        schemaHasType(resolved, "object") ||
        resolved.properties ||
        resolved.required
    ) {
        if (!validateType(value, "object")) {
            errors.push(`${path} expected object`);
            return errors;
        }

        const objectValue = value as Record<string, unknown>;
        for (const key of resolved.required ?? []) {
            if (!(key in objectValue)) {
                errors.push(`${path}.${key} is required`);
            }
        }

        for (const [key, childSchema] of Object.entries(
            resolved.properties ?? {},
        )) {
            if (key in objectValue) {
                errors.push(
                    ...validateSchema(
                        objectValue[key],
                        childSchema,
                        `${path}.${key}`,
                    ),
                );
            }
        }
    }

    if (
        schemaHasType(resolved, "array") &&
        Array.isArray(value) &&
        resolved.items
    ) {
        value.forEach((item, index) => {
            errors.push(
                ...validateSchema(item, resolved.items!, `${path}[${index}]`),
            );
        });
    }

    return errors;
}

export function expectOpenApiResponse(
    path: string,
    status: number,
    body: unknown,
): void {
    const schema =
        spec.paths[path]?.get?.responses?.[String(status)]?.content?.[
            "application/json"
        ]?.schema;

    if (!schema) {
        throw new Error(
            `Missing OpenAPI response schema for GET ${path} ${status}`,
        );
    }

    const errors = validateSchema(body, schema, "$");
    if (errors.length > 0) {
        throw new Error(
            `GET ${path} ${status} does not match OpenAPI schema:\n${errors.join(
                "\n",
            )}`,
        );
    }
}
