"use client";

import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import type { ToolCallInfo } from "@/lib/api";

export interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    toolCalls?: ToolCallInfo[];
}

interface Props {
    messages: ChatMessage[];
    loading: boolean;
    onSuggestionClick: (text: string) => void;
}

const SUGGESTIONS = [
    "What's the overall health of my database?",
    "How many active connections are there right now?",
    "Is there any replication lag?",
    "Why is my database running slow?",
];

export default function ChatWindow({
    messages,
    loading,
    onSuggestionClick,
}: Props) {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    return (
        <div className="chat-window">
            {messages.length === 0 && !loading && (
                <div className="chat-window__empty">
                    <div className="chat-window__empty-glow" />
                    <div className="chat-window__empty-icon">
                        <svg
                            width="48"
                            height="48"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.2"
                        >
                            <path d="M12 2L2 7l10 5 10-5-10-5z" />
                            <path d="M2 17l10 5 10-5" />
                            <path d="M2 12l10 5 10-5" />
                        </svg>
                    </div>
                    <h2>PostgreSQL Observability Agent</h2>
                    <p className="chat-window__subtitle">
                        AI-powered database monitoring — ask about health, performance,
                        connections, or anything else.
                    </p>
                    <div className="chat-window__suggestions">
                        {SUGGESTIONS.map((s) => (
                            <button
                                key={s}
                                className="suggestion"
                                onClick={() => onSuggestionClick(s)}
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
                                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                                </svg>
                                {s}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            <div className="chat-window__messages">
                {messages.map((msg) => (
                    <MessageBubble
                        key={msg.id}
                        role={msg.role}
                        content={msg.content}
                        toolCalls={msg.toolCalls}
                    />
                ))}

                {loading && (
                    <div className="message message--assistant">
                        <div className="message__avatar">
                            <svg
                                width="18"
                                height="18"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="1.5"
                            >
                                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                                <path d="M2 17l10 5 10-5" />
                                <path d="M2 12l10 5 10-5" />
                            </svg>
                        </div>
                        <div className="message__body">
                            <div className="message__role">Agent</div>
                            <div className="thinking-indicator">
                                <div className="thinking-dot" />
                                <div className="thinking-dot" />
                                <div className="thinking-dot" />
                            </div>
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>
        </div>
    );
}
