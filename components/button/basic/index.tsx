import { Button } from "../../ui/button";

interface BasicButtonInterface {
    clickHandle: () => void;
    text: string;
}
export function BasicButton({ clickHandle, text }: BasicButtonInterface) {
    return <Button onClick={clickHandle}>{text}</Button>;
}
