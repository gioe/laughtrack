export function flatten<T>(arrays: T[][]): T[] {
    return arrays
      .flatMap((array: T[]) => {
        return array.map((object: T) => object)
      })
  }

export function getRandomElement(array: any[]): any {
  const randomIndex = Math.floor(Math.random() * array.length)
  return array[randomIndex]
}
