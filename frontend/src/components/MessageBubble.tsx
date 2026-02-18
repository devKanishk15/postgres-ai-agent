"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism";
import type { ToolCallInfo } from "@/lib/api";
import ToolCallTrace from "./ToolCallTrace";
import type { CSSProperties } from "react";

interface Props {
    role: "user" | "assistant";
    content: string;
    toolCalls?: ToolCallInfo[];
}

export default function MessageBubble({ role, content, toolCalls }: Props) {
    return (
        <div className={`message message--${role}`}>
            <div className="message__avatar">
                {role === "user" ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                    </svg>
                ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M12 2L2 7l10 5 10-5-10-5z" />
                        <path d="M2 17l10 5 10-5" />
                        <path d="M2 12l10 5 10-5" />
                    </svg>
                )}
            </div>
            <div className="message__body">
                <div className="message__role">{role === "user" ? "You" : "Agent"}</div>
                <div className="message__content">
                    {role === "assistant" ? (
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                                code({ className, children, ...props }) {
                                    const match = /language-(\w+)/.exec(className || "");
                                    const inline = !match;
                                    return inline ? (
                                        <code className="inline-code" {...props}>
                                            {children}
                                        </code>
                                    ) : (
                                        <SyntaxHighlighter
                                            style={oneDark as Record<string, CSSProperties>}
                                            language={match[1]}
                                            PreTag="div"
                                            customStyle={{
                                                borderRadius: "8px",
                                                fontSize: "0.85rem",
                                                margin: "0.75rem 0",
                                                border: "1px solid rgba(255,255,255,0.06)",
                                            }}
                                        >
                                            {String(children).replace(/\n$/, "")}
                                        </SyntaxHighlighter>
                                    );
                                },
                                table({ children }) {
                                    return (
                                        <div className="table-wrapper">
                                            <table>{children}</table>
                                        </div>
                                    );
                                },
                            }}
                        >
                            {content}
                        </ReactMarkdown>
                    ) : (
                        <p>{content}</p>
                    )}
                </div>

                {toolCalls && toolCalls.length > 0 && (
                    <ToolCallTrace toolCalls={toolCalls} />
                )}
            </div>
        </div>
    );
}
