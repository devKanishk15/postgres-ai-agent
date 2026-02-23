const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface DatabaseItem {
    name: string;
    label: string;
    job?: string | null;
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

export interface JobDetectionResult {
    database: string;
    job: string | null;
    instance: string | null;
    source: "config" | "prometheus" | "not_found";
}

export async function fetchDatabases(): Promise<DatabaseItem[]> {
    console.log("[API] fetchDatabases — requesting...");
    const res = await fetch(`${API_BASE}/databases`);
    if (!res.ok) {
        console.error("[API] fetchDatabases FAILED:", res.status, res.statusText);
        throw new Error("Failed to fetch databases");
    }
    const data = await res.json();
    console.log("[API] fetchDatabases — received:", data.databases?.length, "databases");
    return data.databases;
}

export async function fetchJobs(): Promise<string[]> {
    console.log("[API] fetchJobs — requesting...");
    const res = await fetch(`${API_BASE}/jobs`);
    if (!res.ok) {
        console.error("[API] fetchJobs FAILED:", res.status, res.statusText);
        throw new Error("Failed to fetch jobs");
    }
    const data = await res.json();
    console.log("[API] fetchJobs — received:", data.jobs);
    return data.jobs;
}

export async function fetchDbTypes(jobName: string): Promise<string[]> {
    console.log(`[API] fetchDbTypes — requesting for job='${jobName}'...`);
    const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobName)}/db_types`);
    if (!res.ok) {
        console.error("[API] fetchDbTypes FAILED:", res.status, res.statusText);
        throw new Error("Failed to fetch db types");
    }
    const data = await res.json();
    console.log(`[API] fetchDbTypes — received for '${jobName}':`, data.db_types);
    return data.db_types;
}

export async function fetchDatabaseJob(name: string): Promise<JobDetectionResult> {
    console.log(`[API] fetchDatabaseJob — requesting for '${name}'...`);
    const res = await fetch(`${API_BASE}/databases/${encodeURIComponent(name)}/job`);
    if (!res.ok) {
        console.error("[API] fetchDatabaseJob FAILED:", res.status, res.statusText);
        throw new Error(`Failed to fetch job for database: ${name}`);
    }
    const data = await res.json();
    console.log(`[API] fetchDatabaseJob — result:`, data);
    return data;
}

export async function sendMessage(
    message: string,
    database: string,
    dbType: string,
    conversationId: string,
    history: HistoryMessage[]
): Promise<ChatResponseData> {
    console.log(`[API] sendMessage — database='${database}', dbType='${dbType}', conv='${conversationId}', historyLen=${history.length}`);
    console.log(`[API] sendMessage — message: ${message.substring(0, 300)}`);
    const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message,
            database,
            db_type: dbType,
            conversation_id: conversationId,
            history,
        }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        console.error("[API] sendMessage FAILED:", res.status, err);
        throw new Error(err.detail || "Chat request failed");
    }
    const data: ChatResponseData = await res.json();
    console.log(`[API] sendMessage — response received: ${data.response?.length} chars, ${data.tool_calls?.length} tool calls`);
    if (data.tool_calls?.length) {
        data.tool_calls.forEach((tc, i) => {
            console.log(`[API]   Tool[${i}]: ${tc.tool}`, tc.args);
            console.log(`[API]   Tool[${i}] result (${tc.result?.length} chars):`, tc.result?.substring(0, 200));
        });
    }
    return data;
}
