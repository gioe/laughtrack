import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";

export default async function AboutLayout({
    children,
    params,
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
