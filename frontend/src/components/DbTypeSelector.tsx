"use client";

import { useState, useEffect, useRef } from "react";
import { fetchDbTypes } from "@/lib/api";

interface Props {
    value: string;
    database: string;
    onChange: (type: string) => void;
}

export default function DbTypeSelector({ value, database, onChange }: Props) {
    const [dbTypes, setDbTypes] = useState<string[]>([]);
    const [search, setSearch] = useState("");
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!database) {
            setDbTypes([]);
            return;
        }
        fetchDbTypes(database)
            .then(setDbTypes)
            .catch(() => setDbTypes([]));
    }, [database]);

    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node))
                setOpen(false);
        }
        document.addEventListener("mousedown", handleClick);
        return () => document.removeEventListener("mousedown", handleClick);
    }, []);

    const filtered = dbTypes.filter(
        (t) => t.toLowerCase().includes(search.toLowerCase())
    );

    const handleSelect = (t: string) => {
        onChange(t);
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
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" />
                </svg>
                <span className="db-selector__label">
                    {value ? value : "DB Type"}
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
                            placeholder="Search DB Type…"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            autoFocus
                        />
                    </div>
                    <ul className="db-selector__list">
                        {filtered.length === 0 && (
                            <li className="db-selector__empty">No DB types found</li>
                        )}
                        {filtered.map((t) => (
                            <li
                                key={t}
                                className={`db-selector__item ${t === value ? "active" : ""
                                    }`}
                                onClick={() => handleSelect(t)}
                            >
                                <span className="db-selector__item-dot" />
                                <div className="db-selector__item-info">
                                    <span className="db-selector__item-label">{t}</span>
                                </div>
                                {t === value && (
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
