export async function runTasks<T>(tasks: Promise<T>[]) {
    return Promise.all(tasks)
  }

export function emptyStringArrayPromise(): Promise<string[]> {
  return new Promise((resolve) => {
    resolve([]);
  });
}

export function emptyStringPromise(): Promise<string> {
  return new Promise((resolve) => {
    resolve("");
  });
}

export function providedStringPromise(input: string): Promise<string> {
  return new Promise((resolve) => {
    resolve(input);
  });
}

export function delay(time: number) {
  return new Promise(function(resolve) { 
      setTimeout(resolve, time)
  });
}