export function flatten<T>(arrays: T[][]): T[] {
    return arrays
      .flatMap((array: T[]) => {
        return array.map((object: T) => object)
      })
  }
