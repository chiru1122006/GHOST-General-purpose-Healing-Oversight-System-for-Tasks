"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Dot,
} from "recharts";

// ─────────────────────────────────────────────
// AdherenceChart — Recharts line chart
// ─────────────────────────────────────────────

interface TrajectoryPoint {
  step: number;
  score: number | null;
  failure: string | null;
  recovery: string | null;
}

interface AdherenceChartProps {
  trajectory: TrajectoryPoint[];
}

// Custom dot renderer: red for failures, amber for recoveries
function CustomDot(props: any) {
  const { cx, cy, payload } = props;
  if (!payload) return null;

  if (payload.failure) {
    return (
      <circle
        cx={cx}
        cy={cy}
        r={6}
        fill="#ef4444"
        stroke="#ef4444"
        strokeWidth={2}
        opacity={0.9}
      />
    );
  }

  if (payload.recovery) {
    return (
      <circle
        cx={cx}
        cy={cy}
        r={5}
        fill="#f59e0b"
        stroke="#f59e0b"
        strokeWidth={2}
        opacity={0.9}
      />
    );
  }

  return (
    <circle
      cx={cx}
      cy={cy}
      r={3}
      fill="#22c55e"
      stroke="#22c55e"
      strokeWidth={1}
      opacity={0.7}
    />
  );
}

// Custom tooltip
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  return (
    <div
      style={{
        background: "#18181b",
        border: "1px solid #3f3f46",
        borderRadius: "8px",
        padding: "12px",
        fontSize: "12px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
      }}
    >
      <div style={{ color: "#a1a1aa", marginBottom: "4px" }}>Step {data.step}</div>
      <div style={{ fontWeight: 600, color: data.score >= 0.7 ? "#22c55e" : data.score >= 0.4 ? "#f59e0b" : "#ef4444" }}>
        Adherence: {data.score !== null ? data.score.toFixed(3) : "N/A"}
      </div>
      {data.failure && (
        <div style={{ color: "#ef4444", marginTop: "4px" }}>
          ⚠️ Failure: {data.failure}
        </div>
      )}
      {data.recovery && (
        <div style={{ color: "#f59e0b", marginTop: "4px" }}>
          🔧 Recovery: {data.recovery}
        </div>
      )}
    </div>
  );
}

export default function AdherenceChart({ trajectory }: AdherenceChartProps) {
  if (trajectory.length === 0) {
    return (
      <div
        style={{
          background: "var(--card)",
          borderRadius: "12px",
          border: "1px solid var(--border)",
          padding: "48px 24px",
          textAlign: "center",
          color: "var(--muted)",
          fontSize: "14px",
        }}
      >
        No trajectory data yet
      </div>
    );
  }

  return (
    <div
      style={{
        background: "var(--card)",
        borderRadius: "12px",
        border: "1px solid var(--border)",
        padding: "20px",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div>
          <div style={{ fontSize: "14px", fontWeight: 600 }}>Adherence Score</div>
          <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>
            Trajectory over {trajectory.length} steps
          </div>
        </div>
        <div style={{ display: "flex", gap: "16px", fontSize: "11px" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#22c55e", display: "inline-block" }} />
            Score
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#ef4444", display: "inline-block" }} />
            Failure
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#f59e0b", display: "inline-block" }} />
            Recovery
          </span>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={trajectory} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            dataKey="step"
            stroke="#71717a"
            tick={{ fill: "#71717a", fontSize: 11 }}
            axisLine={{ stroke: "#3f3f46" }}
          />
          <YAxis
            domain={[0, 1]}
            stroke="#71717a"
            tick={{ fill: "#71717a", fontSize: 11 }}
            axisLine={{ stroke: "#3f3f46" }}
            tickCount={6}
          />
          <Tooltip content={<CustomTooltip />} />
          {/* Drift threshold line */}
          <ReferenceLine
            y={0.4}
            stroke="#ef4444"
            strokeDasharray="8 4"
            strokeWidth={1.5}
            opacity={0.5}
            label={{ value: "Drift Threshold", position: "right", fill: "#ef4444", fontSize: 10 }}
          />
          {/* Score line */}
          <Line
            type="monotone"
            dataKey="score"
            stroke="#22c55e"
            strokeWidth={2.5}
            dot={<CustomDot />}
            activeDot={{ r: 6, stroke: "#22c55e", strokeWidth: 2, fill: "#18181b" }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
