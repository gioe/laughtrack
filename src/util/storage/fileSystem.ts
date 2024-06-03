import fs from 'fs';

export const writeToFileSystem = (object: any, fileName: string) => {
// Convert the object to a JSON string
const data = JSON.stringify(object, null, 2);

// Write the JSON string to a file
fs.writeFile(fileName, data, (err) => {
    if (err) throw err;
    console.log(`Data written to ${fileName}`);
});

}

export const readJsonFile = (sourceFile: string) => {
    console.log(sourceFile)
    try {
        const data = fs.readFileSync(sourceFile, 'utf8');
        return JSON.parse(data);
    } catch (err) {
        console.error('Error reading file:', err);
    }
};