import OrbitProgress from "react-loading-indicators/OrbitProgress";

export default function Loading() {
    return (
        <div className="flex-grow pt-24 bg-ivory">
            <OrbitProgress variant="track-disc" color="crimson" size="large" />;
        </div>
    );
}
