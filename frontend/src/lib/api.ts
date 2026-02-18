const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface DatabaseItem {
    name: string;
    label: string;
}

export interface ToolCallInfo {
    tool: string;
    args: Record<string, unknown>;
    result: string;
}

export interface ChatResponseData {
    response: string;
    conversation_id: string;
    tool_calls: ToolCallInfo[];
}

export interface HistoryMessage {
    role: "user" | "assistant";
    content: string;
}

export async function fetchDatabases(): Promise<DatabaseItem[]> {
    const res = await fetch(`${API_BASE}/databases`);
    if (!res.ok) throw new Error("Failed to fetch databases");
    const data = await res.json();
    return data.databases;
}

export async function sendMessage(
    message: string,
    database: string,
    conversationId: string,
    history: HistoryMessage[]
): Promise<ChatResponseData> {
    const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message,
            database,
            conversation_id: conversationId,
            history,
        }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || "Chat request failed");
    }
    return res.json();
}
