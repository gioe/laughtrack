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
