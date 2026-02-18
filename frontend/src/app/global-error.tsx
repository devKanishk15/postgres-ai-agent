"use client";

import { useEffect } from "react";

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error(error);
    }, [error]);

    return (
        <html>
            <body>
                <div className="flex flex-col items-center justify-center min-h-screen text-center p-4">
                    <h2 className="text-xl font-bold mb-4 text-red-500">
                        Global Error
                    </h2>
                    <pre className="bg-gray-800 p-4 rounded mb-4 max-w-lg overflow-auto text-left text-xs text-white">
                        {error.message}
                        {error.stack}
                    </pre>
                    <button
                        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                        onClick={() => reset()}
                    >
                        Try again
                    </button>
                </div>
            </body>
        </html>
    );
}
