export type BunnyStorageUploadInput = {
    path: string;
    body: Buffer | Uint8Array;
    contentType: string;
};

export type BunnyStorageUploader = (
    input: BunnyStorageUploadInput,
) => Promise<void>;

export class BunnyStorageError extends Error {
    public readonly status: number | null;

    constructor(message: string, status: number | null = null) {
        super(message);
        this.name = "BunnyStorageError";
        this.status = status;
    }
}

function readEnv() {
    const host = process.env.BUNNY_STORAGE_HOST ?? "storage.bunnycdn.com";
    const zone = process.env.BUNNY_STORAGE_ZONE;
    const accessKey = process.env.BUNNY_STORAGE_ACCESS_KEY;
    if (!zone || !accessKey) {
        throw new BunnyStorageError(
            "Bunny storage configuration missing: set BUNNY_STORAGE_ZONE and BUNNY_STORAGE_ACCESS_KEY",
        );
    }
    return { host, zone, accessKey };
}

export const uploadToBunnyStorage: BunnyStorageUploader = async ({
    path,
    body,
    contentType,
}) => {
    const { host, zone, accessKey } = readEnv();
    const cleanPath = path.replace(/^\/+/, "");
    const url = `https://${host}/${zone}/${cleanPath}`;
    const response = await fetch(url, {
        method: "PUT",
        headers: {
            AccessKey: accessKey,
            "Content-Type": contentType,
        },
        body,
    });
    if (!response.ok) {
        throw new BunnyStorageError(
            `Bunny storage upload failed for ${cleanPath}: HTTP ${response.status}`,
            response.status,
        );
    }
};

export type BunnyStorageDeleter = (path: string) => Promise<void>;

// Best-effort cleanup used after a successful Bunny upload when a subsequent
// step fails (next upload throws, DB transaction rolls back). Callers should
// log-and-swallow errors so a failed cleanup never overrides the original
// failure response surfaced to the client.
export const deleteFromBunnyStorage: BunnyStorageDeleter = async (path) => {
    const { host, zone, accessKey } = readEnv();
    const cleanPath = path.replace(/^\/+/, "");
    const url = `https://${host}/${zone}/${cleanPath}`;
    const response = await fetch(url, {
        method: "DELETE",
        headers: { AccessKey: accessKey },
    });
    // Bunny returns 404 for already-absent objects — treat as success since
    // cleanup is idempotent and only ever called as a best-effort.
    if (!response.ok && response.status !== 404) {
        throw new BunnyStorageError(
            `Bunny storage delete failed for ${cleanPath}: HTTP ${response.status}`,
            response.status,
        );
    }
};
