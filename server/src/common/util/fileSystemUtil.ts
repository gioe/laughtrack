import * as fsPromises from 'fs/promises';
import * as fsSync from 'fs';
import path from 'path';

export const readFileFromFileSystem = async (sourceFile: string): Promise<string> => {
    const filePath = getPath(sourceFile)
    return fsPromises.readFile(filePath, { encoding: 'utf8' })
    .then((data: string) => JSON.parse(data))
    .catch((error: Error) => console.log(error))
};

const getPath = (fileName: string) => {
    return path.join(process.env.DIRECTORY_PATH as string, fileName);
}

export const checkForFileExistence = (path: string) => {
    return fsSync.existsSync(path)
}

export const makeDirectory = (path: string) => {
    console.log(`Creating directory at ${path}`)
    return fsSync.mkdirSync(path)
}