import { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";

export class Navigator {
    router: AppRouterInstance;
    path: string;

    // Constructor
    constructor(path: string, router: AppRouterInstance) {
        this.router = router
        this.path = path
    }

    replaceRoute(params: string) {
        this.router?.replace(`${this.path}?${params}`);
    }

    pushPage(providedPath: string, params?: string) {
        let route = providedPath
        if (params) { route = `/${providedPath}?${params}` }
        this.router?.push(route);

    }
}
