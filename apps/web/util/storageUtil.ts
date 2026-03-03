import * as fsPromises from "fs/promises";
import * as fsSync from "fs";
import path from "path";

export async function readFile(fileName: string): Promise<string> {
    return readFileFromFileSystem(fileName)
}

export const readFileFromFileSystem = async (
    sourceFile: string,
): Promise<string> => {
    const filePath = getPath(sourceFile);
    return fsPromises
        .readFile(filePath, { encoding: "utf8" })
        .then((data: string) => JSON.parse(data))
        .catch((error: Error) => console.log(error));
};

const getPath = (fileName: string) => {
    return path.join(process.env.DIRECTORY_PATH as string, fileName);
};

export const checkForFileExistence = (path: string) => {
    return fsSync.existsSync(path);
};

export const makeDirectory = (path: string) => {
    return fsSync.mkdirSync(path);
};

export function readFileSync(path: string) {
    if (checkForFileExistence(path)) return fsSync.readFileSync(path)
    return undefined
}
