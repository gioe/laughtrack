export function groupByPropertyCount<T>(objects: T[], property: keyof T): Record<string, T[]> {
    const result: Record<string, T[]> = {};
  
    for (const obj of objects) {
      const key = obj[property] as string;
      if (!result[key]) {
        result[key] = [];
      }
      result[key].push(obj);
    }
  
    return result;
  }