import { paramConfigs } from '@/util/filter/util';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback } from 'react';

// Interface for parameter updates
export type ParamKeys = keyof typeof paramConfigs;
type ParamTypes = {
  [K in ParamKeys]: ReturnType<(typeof paramConfigs)[K]['parse']>;
};

export function useUrlParams() {
    const router = useRouter();
    const searchParams = useSearchParams();

    const getTypedParam = useCallback(<K extends ParamKeys>(key: K): any => {
      const config = paramConfigs[key];
      const value = searchParams.get(config.key);
      const parsed = config.parse(value);
      if (config.validate?.(parsed)) {
        return parsed;
      } else {
        return parsed
      }
    }, [searchParams]);

    const setTypedParam = useCallback(<K extends ParamKeys>(
      key: K,
      value: ParamTypes[K]
    ): void => {
      const config = paramConfigs[key];
      if (!config.validate?.(value)) {
        console.warn(`Invalid value for parameter ${key}`);
        return;
      }
      const current = new URLSearchParams(searchParams.toString());
      const stringified = config.stringify(value);

      if (stringified === config.stringify(config.defaultValue)) {
        current.delete(config.key);
      } else {
        current.set(config.key, stringified);
      }
      router.replace(`?${current.toString()}`);
    }, [router, searchParams]);

    const setMultipleTypedParams = useCallback((
      updates: Partial<ParamTypes>,
      providedPath?: string,
    ): void => {
      const current = new URLSearchParams(searchParams.toString());

      (Object.entries(updates) as [ParamKeys, any][]).forEach(([key, value]) => {
        const config = paramConfigs[key];
        console.log(`The value is ${value} for key ${key}`)
        if (!config.validate?.(value)) {
            return;
          }
        console.log(`The key value ${key} is valid`)
        const stringified = config.stringify(value);
        if (stringified === config.stringify(config.defaultValue)) {
          current.delete(config.key);
        } else {
          current.set(config.key, stringified);
        }
      });
      if (providedPath) { router.push(`/${providedPath}?${current.toString()}`); }
      else { router.push(`?${current.toString()}`) }

    }, [router, searchParams]);

    return {
      getTypedParam,
      setTypedParam,
      setMultipleTypedParams
    };
}
