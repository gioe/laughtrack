// generic singleton creator:
export function createSingleton<T>(name: string, create: () => T): T {
    const s = Symbol.for(name);
    const globalScope = global as Record<symbol, T | undefined>;
    let scope = globalScope[s];
    if (!scope) {
        scope = { ...create() } as T;
        globalScope[s] = scope;
    }
    return scope;
}
