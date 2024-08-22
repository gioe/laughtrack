export function flattenElements<T>(arrays: T[][]): T[] {
    return arrays
      .flatMap((array: T[]) => {
        return array.map((object: T) => object)
      })
  }