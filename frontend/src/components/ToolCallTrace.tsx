"use client";

import { useState } from "react";
import type { ToolCallInfo } from "@/lib/api";

interface Props {
    toolCalls: ToolCallInfo[];
}

export default function ToolCallTrace({ toolCalls }: Props) {
    const [expanded, setExpanded] = useState(false);

    return (
        <div className="tool-trace">
            <button
                className="tool-trace__toggle"
                onClick={() => setExpanded(!expanded)}
                type="button"
            >
                <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                >
                    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
                </svg>
                <span>
                    {toolCalls.length} tool call{toolCalls.length > 1 ? "s" : ""} used
                </span>
                <svg
                    className={`tool-trace__arrow ${expanded ? "open" : ""}`}
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                >
                    <polyline points="6 9 12 15 18 9" />
                </svg>
            </button>

            {expanded && (
                <div className="tool-trace__list">
                    {toolCalls.map((tc, i) => (
                        <div key={i} className="tool-trace__item">
                            <div className="tool-trace__name">{tc.tool}</div>
                            <div className="tool-trace__section">
                                <span className="tool-trace__label">Args</span>
                                <pre className="tool-trace__code">
                                    {JSON.stringify(tc.args, null, 2)}
                                </pre>
                            </div>
                            {tc.result && (
                                <div className="tool-trace__section">
                                    <span className="tool-trace__label">Result</span>
                                    <pre className="tool-trace__code">{tc.result}</pre>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
