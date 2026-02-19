"use client";

import { useState } from "react";
import type { ToolCallInfo } from "@/lib/api";

interface Props {
    toolCalls: ToolCallInfo[];
}

function ToolCallItem({ tc, index }: { tc: ToolCallInfo; index: number }) {
    const [open, setOpen] = useState(false);

    return (
        <div className="tc-item">
            <button
                className={`tc-item__header ${open ? "open" : ""}`}
                onClick={() => setOpen(!open)}
                type="button"
            >
                <span className="tc-item__index">{index + 1}</span>
                <span className="tc-item__name">{tc.tool}</span>
                <svg
                    className={`tc-item__chevron ${open ? "open" : ""}`}
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                >
                    <polyline points="6 9 12 15 18 9" />
                </svg>
            </button>

            {open && (
                <div className="tc-item__body">
                    <div className="tc-item__section">
                        <span className="tc-item__label">Arguments</span>
                        <pre className="tc-item__code">
                            {JSON.stringify(tc.args, null, 2)}
                        </pre>
                    </div>
                    {tc.result && (
                        <div className="tc-item__section">
                            <span className="tc-item__label">Result</span>
                            <pre className="tc-item__code">{tc.result}</pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
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
                    width="13"
                    height="13"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                >
                    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
                </svg>
                <span>
                    {toolCalls.length} tool call{toolCalls.length > 1 ? "s" : ""}
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
                        <ToolCallItem key={i} tc={tc} index={i} />
                    ))}
                </div>
            )}
        </div>
    );
}
