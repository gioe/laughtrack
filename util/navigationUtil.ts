'use client';

import { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { usePathname, useRouter } from "next/navigation";

export function pushNewPage(params: URLSearchParams, router: AppRouterInstance, pathname: string) {
    router.push(`/${pathname}?${params.toString()}`);
}

export function replaceRoute(params: URLSearchParams) {

    const { replace } = useRouter();
    const pathname = usePathname();

    replace(`/${pathname}?${params.toString()}`);
}
