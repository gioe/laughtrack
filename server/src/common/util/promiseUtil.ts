export async function executeClauseOrDefault<T> (choice: Promise<T>, defaultOption: T, clause: boolean) {
  if (clause) {
    return choice
  }
  return provideGenericPromiseResponse(defaultOption);
}

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

export function provideGenericPromiseResponse<T>(input: T): Promise<T> {
  return new Promise((resolve) => {
    resolve(input);
  });
}

export function emptyUndefinedPromise(): Promise<undefined> {
  return new Promise((resolve) => {
    resolve(undefined)
  });
}

