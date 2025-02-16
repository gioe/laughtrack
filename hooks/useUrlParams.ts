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
      return parsed
    }, [searchParams]);

    const setTypedParam = useCallback(<K extends ParamKeys>(
      key: K,
      value: ParamTypes[K]
    ): void => {
      const config = paramConfigs[key];

      const current = new URLSearchParams(searchParams.toString());
      const stringified = config.stringify(value);

      if (stringified === config.stringify(config.defaultValue)) {
        current.delete(config.key);
      } else {
        current.set(config.key, stringified);
      }

      router.push(`?${current.toString()}`);
    }, [router, searchParams]);

    const setMultipleTypedParams = useCallback((
      updates: Partial<ParamTypes>
    ): void => {
      const current = new URLSearchParams(searchParams.toString());

      (Object.entries(updates) as [ParamKeys, any][]).forEach(([key, value]) => {
        const config = paramConfigs[key];

        const stringified = config.stringify(value);
        if (stringified === config.stringify(config.defaultValue)) {
          current.delete(config.key);
        } else {
          current.set(config.key, stringified);
        }
      });

      router.push(`?${current.toString()}`);
    }, [router, searchParams]);

    return {
      getTypedParam,
      setTypedParam,
      setMultipleTypedParams
    };
}
