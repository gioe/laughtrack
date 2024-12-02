import { Button } from "../../ui/button";

interface BasicButtonInterface {
    clickHandle: () => void;
    text: string;
    isLoading: boolean;
}
export function BasicButton({
    clickHandle,
    text,
    isLoading,
}: BasicButtonInterface) {
    return (
        <Button onClick={clickHandle} disabled={isLoading}>
            {text}
        </Button>
    );
}
