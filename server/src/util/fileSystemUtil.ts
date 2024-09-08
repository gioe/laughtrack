import fs from 'fs/promises';
import path from 'path';

export const readFile = async (sourceFile: string): Promise<string> => {
    const filePath = getPath(sourceFile)
    return fs.readFile(filePath, { encoding: 'utf8' })
    .then((data: string) => JSON.parse(data))
    .catch((error: Error) => console.log(error))
};

const getPath = (fileName: string) => {
    return path.join(process.env.DIRECTORY_PATH as string, fileName);
}