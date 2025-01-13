"use client";

import { SocialData } from "@/objects/class/socialData/SocialData";
import { Tooltip } from "@material-tailwind/react";
import { useRouter } from "next/navigation";

interface SocialMediaBarProps {
    data: SocialData;
}

const SocialMediaBar: React.FC<SocialMediaBarProps> = ({ data }) => {
    const router = useRouter();
    const hasInstagram = data.instagram.account !== null;
    const hasTikTok = data.tiktok.account !== null;
    const hasYouTube = data.youtube.account !== null;

    const goTo = (url: string) => {
        router.push(url);
    };

    return (
        <div className="flex gap-4 justify-center items-center h-6">
            {hasInstagram && (
                <Tooltip content={`${data.instagram.account}`}>
                    <span
                        className="cursor-pointer rounded-full border border-gray-900/5 bg-gray-900/5 p-3 text-gray-900 transition-colors hover:border-gray-900/10 hover:bg-gray-900/10 hover:!opacity-100 group-hover:opacity-70"
                        onClick={() =>
                            goTo(
                                `https://instagram.com/${data.instagram.account}`,
                            )
                        }
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width={20}
                            height={20}
                            viewBox="0 0 24 24"
                            stroke="#232604"
                            fill="none"
                        >
                            <path
                                strokeLinejoin="round"
                                d="M3.062 7.245c.046-1.022.206-1.681.423-2.241l.003-.008c.214-.57.55-1.085.984-1.511l.006-.006.006-.006c.427-.435.943-.77 1.512-.984l.01-.004c.558-.217 1.216-.377 2.238-.423M3.062 7.245C3.012 8.337 3 8.675 3 11.506c0 2.832.012 3.17.062 4.262m0-8.523v.275m.427 10.497a4.18 4.18 0 0 0 .984 1.511l.006.006.006.006c.426.434.942.77 1.511.985l.009.003c.559.217 1.217.376 2.24.423m-4.756-2.934-.004-.01c-.217-.558-.377-1.216-.423-2.239m.427 2.249-.013-.068m-.414-2.181.016.088m-.016-.088v-.276m.414 2.457-.398-2.093m.398 2.093c-.169-.446-.343-1.068-.398-2.093m.398 2.093.018.046c.214.578.553 1.1.993 1.53.43.44.952.78 1.53.994.462.18 1.115.369 2.227.42 1.123.05 1.47.061 4.262.061 2.793 0 3.14-.01 4.262-.061 1.114-.052 1.766-.241 2.227-.42a4.166 4.166 0 0 0 1.53-.993c.44-.43.78-.953.994-1.53.18-.463.369-1.115.42-2.228.05-1.123.061-1.47.061-4.262 0-2.791-.01-3.14-.062-4.262-.05-1.12-.242-1.772-.422-2.234a4.159 4.159 0 0 0-.991-1.524 4.164 4.164 0 0 0-1.522-.99c-.463-.18-1.116-.37-2.235-.422a170.15 170.15 0 0 0-.276-.012M3.078 15.856a165.497 165.497 0 0 1-.017-.364m5.183-13.43C9.337 2.012 9.675 2 12.506 2c2.831 0 3.17.013 4.261.062m-8.523 0h.277m8.246 0h-.275m.275 0c1.023.046 1.682.206 2.242.423l.007.003c.57.214 1.085.55 1.512.984l.006.006.006.006c.434.427.77.942.984 1.512l.003.01c.218.558.377 1.216.424 2.239M8.52 2.062h7.971m-7.971 0c.924-.04 1.436-.05 3.985-.05 2.55 0 3.061.01 3.986.05m-7.971 0-.277.012c-1.114.051-1.766.24-2.227.42a4.166 4.166 0 0 0-1.535.998c-.454.456-.751.912-.985 1.517-.182.464-.372 1.117-.423 2.235l-.012.276m18.889 8.248c-.047 1.023-.206 1.681-.423 2.24l-.003.008a4.187 4.187 0 0 1-.985 1.512l-.006.006-.006.006a4.18 4.18 0 0 1-1.511.984l-.01.004c-.558.217-1.216.376-2.239.423M3.062 15.49c-.04-.924-.05-1.435-.05-3.985s.01-3.06.05-3.986m0 7.972V7.52m7.754 8.068a4.418 4.418 0 1 0 3.381-8.164 4.418 4.418 0 0 0-3.381 8.164ZM9.372 8.372a4.432 4.432 0 1 1 6.268 6.268 4.432 4.432 0 0 1-6.268-6.268Zm10.062-2.33a1.269 1.269 0 1 1-2.538 0 1.269 1.269 0 0 1 2.538 0Z"
                            />
                        </svg>
                    </span>
                </Tooltip>
            )}

            {hasTikTok && (
                <Tooltip content={`${data.tiktok.account}`}>
                    <span
                        className="cursor-pointer rounded-full border border-gray-900/5 bg-gray-900/5 p-3 text-gray-900 transition-colors hover:border-gray-900/10 hover:bg-gray-900/10 hover:!opacity-100 group-hover:opacity-70"
                        onClick={() =>
                            goTo(`https://tiktok.com/@${data.tiktok.account}`)
                        }
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width={20}
                            height={20}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="#232604"
                        >
                            <path
                                strokeLinejoin="round"
                                d="M16.822 5.134A4.75 4.75 0 0 1 15.648 2h-.919m2.093 3.134a4.773 4.773 0 0 0 3.605 1.649v3.436a8.172 8.172 0 0 1-4.78-1.537v6.989c0 3.492-2.839 6.329-6.323 6.329-1.824 0-3.47-.78-4.626-2.02A6.31 6.31 0 0 1 3 15.67c0-3.44 2.756-6.245 6.17-6.32m7.652-4.216a5.512 5.512 0 0 1-.054-.035M6.985 17.352a2.859 2.859 0 0 1-.547-1.686 2.89 2.89 0 0 1 2.886-2.888c.297 0 .585.05.854.134v-3.51a6.418 6.418 0 0 0-.854-.06c-.051 0-.462.027-.513.027M14.724 2H12.21l-.005 13.777a2.89 2.89 0 0 1-2.881 2.782 2.898 2.898 0 0 1-2.343-1.203"
                            />
                        </svg>
                    </span>
                </Tooltip>
            )}

            {hasYouTube && (
                <Tooltip content={data.youtube.account}>
                    <span
                        className="cursor-pointer rounded-full border border-gray-900/5 bg-gray-900/5 p-3 text-gray-900 transition-colors hover:border-gray-900/10 hover:bg-gray-900/10 hover:!opacity-100 group-hover:opacity-70"
                        onClick={() =>
                            goTo(
                                `https://www.youtube.com/@${data.youtube.account}`,
                            )
                        }
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width={20}
                            height={20}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="#232604"
                        >
                            <path
                                strokeLinejoin="round"
                                d="M20.595 4.46a2.755 2.755 0 0 1 1.945 1.945C22.998 8.12 23 11.7 23 11.7s0 3.58-.46 5.296a2.755 2.755 0 0 1-1.945 1.945C18.88 19.4 12 19.4 12 19.4s-6.88 0-8.595-.46a2.755 2.755 0 0 1-1.945-1.945C1 15.28 1 11.7 1 11.7s0-3.58.46-5.295A2.755 2.755 0 0 1 3.405 4.46C5.12 4 12 4 12 4s6.88 0 8.595.46Zm-5.082 7.24L9.798 15V8.401l5.715 3.3Z"
                                clipRule="evenodd"
                            />
                        </svg>
                    </span>
                </Tooltip>
            )}

            {data.website && (
                <Tooltip content={data.website}>
                    <span
                        className="cursor-pointer rounded-full border border-gray-900/5 bg-gray-900/5 p-3 text-gray-900 transition-colors hover:border-gray-900/10 hover:bg-gray-900/10 hover:!opacity-100 group-hover:opacity-70"
                        onClick={() => goTo(data.website)}
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width={20}
                            height={20}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="#232604"
                        >
                            <path
                                stroke="#000"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={1.5}
                                d="M17.5 3h-11A4.27 4.27 0 0 0 2 7v6a4.27 4.27 0 0 0 4.5 4h11a4.27 4.27 0 0 0 4.5-4V7a4.27 4.27 0 0 0-4.5-4v0ZM12 17v4M15.9 21h-8"
                            />
                        </svg>
                    </span>
                </Tooltip>
            )}
        </div>
    );
};

export default SocialMediaBar;
