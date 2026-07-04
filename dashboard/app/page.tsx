"use client";

import { useEffect, useState, useCallback } from "react";
import StatsHeader from "./components/StatsHeader";
import SessionTable from "./components/SessionTable";
import AdherenceChart from "./components/AdherenceChart";
import FailureAlert from "./components/FailureAlert";
import RecoveryLog from "./components/RecoveryLog";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

interface Session {
  session_id: string;
  task_type: string;
  objective: string;
  status: string;
  total_steps: number;
  recovery_count: number;
  final_adherence: number | null;
  success: boolean;
  duration_seconds: number | null;
}

interface Step {
  step_number: number;
  tool_name: string;
  tool_input: string | null;
  tool_output: string | null;
  tool_error: string | null;
  adherence_score: number | null;
  failure_detected: boolean;
  failure_type: string | null;
  recovery_triggered: boolean;
  recovery_strategy: string | null;
  timestamp: number | null;
}

interface SessionDetail extends Session {
  steps: Step[];
}

interface TrajectoryPoint {
  step: number;
  score: number | null;
  failure: string | null;
  recovery: string | null;
}

interface Stats {
  total_sessions: number;
  successful_sessions: number;
  success_rate: number;
  total_recoveries: number;
  total_failures: number;
  failure_breakdown: Record<string, number>;
  avg_adherence: number;
}

// ─────────────────────────────────────────────
// API Base
// ─────────────────────────────────────────────

const API_BASE = "/api";

// ─────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [trajectory, setTrajectory] = useState<TrajectoryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch stats + session list
  const fetchOverview = useCallback(async () => {
    try {
      const [statsRes, sessionsRes] = await Promise.all([
        fetch(`${API_BASE}/stats`),
        fetch(`${API_BASE}/sessions`),
      ]);

      if (!statsRes.ok || !sessionsRes.ok) {
        throw new Error("API returned an error. Is the FastAPI server running?");
      }

      setStats(await statsRes.json());
      const sessionList = await sessionsRes.json();
      setSessions(sessionList);

      // Auto-select first session if none selected
      if (!selectedId && sessionList.length > 0) {
        setSelectedId(sessionList[0].session_id);
      }

      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to connect to API");
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  // Fetch selected session detail + trajectory
  const fetchDetail = useCallback(async (id: string) => {
    try {
      const [detailRes, trajRes] = await Promise.all([
        fetch(`${API_BASE}/sessions/${id}`),
        fetch(`${API_BASE}/sessions/${id}/trajectory`),
      ]);

      if (detailRes.ok) setDetail(await detailRes.json());
      if (trajRes.ok) setTrajectory(await trajRes.json());
    } catch {
      // Silently fail — the overview still works
    }
  }, []);

  // Initial load + polling
  useEffect(() => {
    fetchOverview();
    const interval = setInterval(fetchOverview, 5000);
    return () => clearInterval(interval);
  }, [fetchOverview]);

  // Load detail when selection changes
  useEffect(() => {
    if (selectedId) fetchDetail(selectedId);
  }, [selectedId, fetchDetail]);

  // Handle session click
  const handleSelect = (id: string) => {
    setSelectedId(id);
  };

  // ─────────────────────────────────────────
  // Error state
  // ─────────────────────────────────────────
  if (error) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: "16px",
      }}>
        <div style={{
          fontSize: "48px",
          fontWeight: 800,
          background: "linear-gradient(135deg, #ef4444 0%, #f59e0b 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}>
          GHOST
        </div>
        <div style={{ color: "var(--muted)", maxWidth: "400px", textAlign: "center" }}>
          <p style={{ marginBottom: "8px", fontWeight: 600 }}>Cannot connect to API</p>
          <p style={{ fontSize: "14px" }}>{error}</p>
          <p style={{ fontSize: "13px", marginTop: "12px", opacity: 0.6 }}>
            Make sure the FastAPI server is running:<br />
            <code style={{ color: "var(--amber)" }}>uvicorn api.main:app --reload --port 8000</code>
          </p>
        </div>
        <button
          onClick={() => { setLoading(true); setError(null); fetchOverview(); }}
          style={{
            marginTop: "12px",
            padding: "10px 24px",
            borderRadius: "8px",
            border: "1px solid var(--border)",
            background: "var(--card)",
            color: "var(--foreground)",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: 500,
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  // ─────────────────────────────────────────
  // Loading state
  // ─────────────────────────────────────────
  if (loading) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: "16px",
      }}>
        <div style={{
          fontSize: "48px",
          fontWeight: 800,
          background: "linear-gradient(135deg, #22c55e 0%, #3b82f6 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}>
          GHOST
        </div>
        <div style={{ color: "var(--muted)", fontSize: "14px" }}>Loading dashboard...</div>
      </div>
    );
  }

  // ─────────────────────────────────────────
  // Main Layout
  // ─────────────────────────────────────────
  return (
    <div style={{ minHeight: "100vh", padding: "24px", maxWidth: "1600px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: "24px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{
            fontSize: "28px",
            fontWeight: 800,
            background: "linear-gradient(135deg, #22c55e 0%, #3b82f6 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}>
            GHOST
          </span>
          <span style={{
            fontSize: "13px",
            color: "var(--muted)",
            padding: "4px 8px",
            borderRadius: "6px",
            border: "1px solid var(--border)",
          }}>
            Agent Monitor
          </span>
        </div>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          fontSize: "13px",
          color: "var(--muted)",
        }}>
          <span style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: "var(--green)",
            display: "inline-block",
            boxShadow: "0 0 6px var(--green)",
          }} />
          Live
        </div>
      </div>

      {/* Stats Cards */}
      {stats && <StatsHeader stats={stats} />}

      {/* Main Content: Two Columns */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "400px 1fr",
        gap: "24px",
        marginTop: "24px",
      }}>
        {/* Left: Session Table */}
        <SessionTable
          sessions={sessions}
          selectedId={selectedId}
          onSelect={handleSelect}
        />

        {/* Right: Detail Panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {detail ? (
            <>
              {/* Session Header */}
              <div style={{
                background: "var(--card)",
                borderRadius: "12px",
                padding: "16px 20px",
                border: "1px solid var(--border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}>
                <div>
                  <div style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "4px" }}>
                    Session
                  </div>
                  <div style={{ fontFamily: "monospace", fontSize: "14px", fontWeight: 600 }}>
                    {detail.session_id}
                  </div>
                </div>
                <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>
                      Task
                    </div>
                    <div style={{ fontSize: "14px", fontWeight: 500 }}>{detail.task_type}</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>
                      Steps
                    </div>
                    <div style={{ fontSize: "14px", fontWeight: 500 }}>{detail.total_steps}</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>
                      Status
                    </div>
                    <span style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      padding: "2px 10px",
                      borderRadius: "12px",
                      background: detail.status === "completed" ? "#22c55e20" : detail.status === "failed" ? "#ef444420" : "#3b82f620",
                      color: detail.status === "completed" ? "var(--green)" : detail.status === "failed" ? "var(--red)" : "var(--blue)",
                    }}>
                      {detail.status}
                    </span>
                  </div>
                </div>
              </div>

              {/* Adherence Chart */}
              <AdherenceChart trajectory={trajectory} />

              {/* Failure + Recovery side by side */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
                <FailureAlert steps={detail.steps} />
                <RecoveryLog steps={detail.steps} />
              </div>
            </>
          ) : (
            <div style={{
              background: "var(--card)",
              borderRadius: "12px",
              padding: "48px",
              border: "1px solid var(--border)",
              textAlign: "center",
              color: "var(--muted)",
              fontSize: "14px",
            }}>
              Select a session to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
