import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";

export default async function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
    params: Promise<{ name: string }>;
}) {
    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            {children}
        </StyleContextProvider>
    );
}
