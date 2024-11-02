export async function runTasks<T>(tasks: Promise<T>[]) {
    return Promise.all(tasks);
}

export function delay(time: number) {
    return new Promise(function (resolve) {
        setTimeout(resolve, time);
    });
}

export function providedPromiseResponse<T>(input: T): Promise<T> {
    return new Promise((resolve) => {
        resolve(input);
    });
}
