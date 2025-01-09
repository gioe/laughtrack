const copyBlocks = [
    "Laughtrack is a space to find things that make you laugh, and hopefully nothing else.",
    "Follow comedians you like. We'll let you know when they're in your area. You wouldn't want to miss that one time that one person on that one podcast was at a club near you, would you?",
    "Search for shows of your liking. We'll put them all in front of you and let you know which we think you'll like. We'll even show you places and shows you probably didn't even know existed.",
    "We just want to clean up the comedy space a little bit. Enjoying yourself shouldn't be so hard",
];

const AboutPage = async () => {
    return (
        <main className="flex-grow pt-24 bg-ivory">
            <section className="max-w-7xl mx-auto text-left ml-5">
                <h2 className="font-fjalla text-5xl text-copper p-5">
                    About this
                </h2>
                <div className="flex flex-col gap-3"></div>
                {copyBlocks.map((block: string) => {
                    return (
                        <div className="font-fjalla text-2xl text-copper p-5">
                            {block}
                        </div>
                    );
                })}
            </section>
        </main>
    );
};

export default AboutPage;
