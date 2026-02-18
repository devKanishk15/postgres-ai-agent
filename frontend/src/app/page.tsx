"use client";

import { useState, useRef, useCallback, type KeyboardEvent } from "react";
import { v4 as uuidv4 } from "uuid";
import ChatWindow from "@/components/ChatWindow";
import DatabaseSelector from "@/components/DatabaseSelector";
import type { ChatMessage } from "@/components/ChatWindow";
import type { HistoryMessage, ToolCallInfo } from "@/lib/api";
import { sendMessage } from "@/lib/api";

export default function Home() {
  const [database, setDatabase] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId] = useState(() => uuidv4());
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleDatabaseChange = useCallback((name: string) => {
    setDatabase(name);
  }, []);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    if (!database) {
      const errMsg: ChatMessage = {
        id: uuidv4(),
        role: "assistant",
        content:
          "⚠️ Please select a database from the dropdown in the top-left corner before sending a message.",
      };
      setMessages((prev) => [...prev, errMsg]);
      return;
    }

    const userMsg: ChatMessage = { id: uuidv4(), role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    // reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    const history: HistoryMessage[] = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const res = await sendMessage(text, database, conversationId, history);
      const assistantMsg: ChatMessage = {
        id: uuidv4(),
        role: "assistant",
        content: res.response,
        toolCalls: res.tool_calls as ToolCallInfo[],
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errorText = err instanceof Error ? err.message : "Unknown error";
      const errMsg: ChatMessage = {
        id: uuidv4(),
        role: "assistant",
        content: `❌ **Error:** ${errorText}\n\nPlease try again or check that the backend is running.`,
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  }, [input, loading, database, messages, conversationId]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  };

  const handleSuggestionClick = (text: string) => {
    setInput(text);
    textareaRef.current?.focus();
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header__left">
          <DatabaseSelector
            value={database}
            onChange={handleDatabaseChange}
          />
        </div>
        <div className="header__center">
          <h1 className="header__title">PostgreSQL Agent</h1>
        </div>
        <div className="header__right">
          <div className="header__status">
            <span className={`header__dot ${database ? "active" : ""}`} />
            <span className="header__status-text">
              {database ? database : "No DB selected"}
            </span>
          </div>
        </div>
      </header>

      {/* Chat */}
      <main className="main">
        <ChatWindow
          messages={messages}
          loading={loading}
          onSuggestionClick={handleSuggestionClick}
        />
      </main>

      {/* Input Bar */}
      <footer className="input-bar">
        <div className="input-bar__container">
          <textarea
            ref={textareaRef}
            className="input-bar__textarea"
            placeholder={
              database
                ? `Ask about ${database}…`
                : "Select a database first…"
            }
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={loading}
          />
          <button
            className="input-bar__send"
            onClick={handleSend}
            disabled={loading || !input.trim()}
            title="Send message"
            type="button"
          >
            {loading ? (
              <span className="input-bar__spinner" />
            ) : (
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            )}
          </button>
        </div>
        <p className="input-bar__hint">
          Press <kbd>Enter</kbd> to send, <kbd>Shift+Enter</kbd> for new line
        </p>
      </footer>
    </div>
  );
}
