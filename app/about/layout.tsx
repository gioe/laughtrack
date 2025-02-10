import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";

export default function AboutPageLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            {children}
        </StyleContextProvider>
    );
}
