"use client";

import { useState, useEffect, useRef } from "react";
import { fetchJobs } from "@/lib/api";

interface Props {
    value: string;
    onChange: (name: string) => void;
}

export default function DatabaseSelector({ value, onChange }: Props) {
    const [jobs, setJobs] = useState<string[]>([]);
    const [search, setSearch] = useState("");
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        fetchJobs()
            .then(setJobs)
            .catch(() => { });
    }, []);

    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node))
                setOpen(false);
        }
        document.addEventListener("mousedown", handleClick);
        return () => document.removeEventListener("mousedown", handleClick);
    }, []);

    const filtered = jobs.filter(
        (j) => j.toLowerCase().includes(search.toLowerCase())
    );

    const handleSelect = (jobName: string) => {
        onChange(jobName);
        setOpen(false);
        setSearch("");
    };

    return (
        <div className="db-selector" ref={ref}>
            <button
                className="db-selector__trigger"
                onClick={() => setOpen(!open)}
                type="button"
            >
                <svg
                    className="db-selector__icon"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                >
                    <ellipse cx="12" cy="5" rx="9" ry="3" />
                    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                </svg>
                <span className="db-selector__label">
                    {value ? value : "Database"}
                </span>
                <svg
                    className={`db-selector__arrow ${open ? "open" : ""}`}
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

            {open && (
                <div className="db-selector__dropdown">
                    <div className="db-selector__search-wrap">
                        <svg
                            className="db-selector__search-icon"
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                        >
                            <circle cx="11" cy="11" r="8" />
                            <path d="M21 21l-4.35-4.35" />
                        </svg>
                        <input
                            className="db-selector__search"
                            type="text"
                            placeholder="Search databases…"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            autoFocus
                        />
                    </div>
                    <ul className="db-selector__list">
                        {filtered.length === 0 && (
                            <li className="db-selector__empty">No databases found</li>
                        )}
                        {filtered.map((j) => (
                            <li
                                key={j}
                                className={`db-selector__item ${j === value ? "active" : ""
                                    }`}
                                onClick={() => handleSelect(j)}
                            >
                                <span className="db-selector__item-dot" />
                                <div className="db-selector__item-info">
                                    <span className="db-selector__item-label">{j}</span>
                                </div>
                                {j === value && (
                                    <svg
                                        className="db-selector__check"
                                        width="16"
                                        height="16"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2.5"
                                    >
                                        <polyline points="20 6 9 17 4 12" />
                                    </svg>
                                )}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
