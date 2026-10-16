import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartSpec } from "../types";

const COLORS = ["#1F4FB8", "#B7CBEF", "#C25E14", "#2E7D4F", "#8A8C90"];

export function Chart({ spec }: { spec: ChartSpec }) {
  const multi = spec.series.length > 1;
  const right = spec.series.some((s) => s.axis === "right");
  const axisOf = (s: ChartSpec["series"][number]) => (s.axis === "right" ? "right" : "left");
  const common = (
    <>
      <CartesianGrid stroke="#EDEDE8" vertical={false} />
      <XAxis dataKey={spec.x_key} tick={{ fontSize: 11, fill: "#5A5D61" }} interval={0} />
      <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "#5A5D61" }} width={36} />
      {right && (
        <YAxis
          yAxisId="right"
          orientation="right"
          domain={[0, 100]}
          unit="%"
          tick={{ fontSize: 11, fill: "#5A5D61" }}
          width={44}
        />
      )}
      <Tooltip formatter={(v) => (v === null || v === undefined ? "no data" : String(v))} />
      {multi && <Legend wrapperStyle={{ fontSize: 12 }} />}
    </>
  );
  return (
    <figure className="chart card">
      <figcaption>{spec.title}</figcaption>
      <div style={{ width: "100%", height: 200, marginTop: 8 }}>
        <ResponsiveContainer>
          {spec.type === "line" ? (
            <LineChart data={spec.data}>
              {common}
              {spec.series.map((s, i) => (
                <Line
                  key={s.key}
                  yAxisId={axisOf(s)}
                  dataKey={s.key}
                  name={s.label}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2.5}
                />
              ))}
            </LineChart>
          ) : (
            <BarChart data={spec.data}>
              {common}
              {spec.series.map((s, i) => (
                <Bar
                  key={s.key}
                  yAxisId={axisOf(s)}
                  dataKey={s.key}
                  name={s.label}
                  fill={s.key.startsWith("previous") ? "#B7CBEF" : COLORS[i % COLORS.length]}
                />
              ))}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
      {/* Screen-reader summary of the drawn values */}
      <p className="sr-only">
        {spec.data
          .map(
            (d) =>
              `${d[spec.x_key]}: ${spec.series.map((s) => `${s.label} ${d[s.key] ?? "no data"}`).join(", ")}`,
          )
          .join("; ")}
      </p>
      {spec.notes.map((n) => (
        <p key={n} className="xsmall muted" style={{ margin: "6px 0 0" }}>
          {n}
        </p>
      ))}
    </figure>
  );
}
