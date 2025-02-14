import { ParamsProvider } from "@/contexts/ParamsProvider";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";

export default async function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
    params: Promise<{ name: string }>;
}) {
    return (
        <ParamsProvider value={""}>
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                {children}
            </StyleContextProvider>
        </ParamsProvider>
    );
}
