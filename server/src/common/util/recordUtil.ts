export function recordKeys<K extends PropertyKey, T>(object: Record<K, T>) {
    return Object.keys(object) as (K)[];
  };
  
  export function recordEntries<K extends PropertyKey, T>(object: Record<K, T>) {
    return Object.entries(object) as ([K,T])[];
  };