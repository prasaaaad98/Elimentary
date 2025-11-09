import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const COLORS = ["#4a9eff", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

export default function MetricsChart({ chartData }) {
  if (!chartData || !chartData.series || chartData.series.length === 0) {
    return null;
  }

  const chartType = chartData.chart_type || "line";

  // Prepare data for Recharts
  // For line/bar charts: create array of { year, metric1, metric2, ... }
  // For pie chart: create array of { name, value }
  let chartFormatData = [];

  if (chartType === "pie") {
    // Pie chart: use the first (and only) year's data
    chartFormatData = chartData.series.map((series) => ({
      name: series.label,
      value: series.values[0] || 0,
    }));
  } else {
    // Line/Bar chart: create data points per year
    chartFormatData = chartData.years.map((year, yearIdx) => {
      const dataPoint = { year: year.toString() };
      chartData.series.forEach((series) => {
        dataPoint[series.label] = series.values[yearIdx] || 0;
      });
      return dataPoint;
    });
  }

  // Custom tooltip for dark theme
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div
          style={{
            background: "rgba(26, 26, 46, 0.95)",
            border: "1px solid rgba(255, 255, 255, 0.2)",
            borderRadius: "8px",
            padding: "12px",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
          }}
        >
          <p style={{ color: "rgba(255, 255, 255, 0.8)", margin: "0 0 8px 0", fontSize: "13px" }}>
            {chartType === "pie" ? label : `Year: ${label}`}
          </p>
          {payload.map((entry, idx) => (
            <p
              key={idx}
              style={{
                color: entry.color,
                margin: "4px 0",
                fontSize: "13px",
                fontWeight: "500",
              }}
            >
              {entry.name}: {typeof entry.value === "number" ? entry.value.toLocaleString() : entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Custom label for pie chart
  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text
        x={x}
        y={y}
        fill="#ffffff"
        textAnchor={x > cx ? "start" : "end"}
        dominantBaseline="central"
        style={{ fontSize: "13px", fontWeight: "500" }}
      >
        {`${(percent * 100).toFixed(1)}%`}
      </text>
    );
  };

  return (
    <div
      style={{
        background: "rgba(255, 255, 255, 0.03)",
        borderRadius: "12px",
        padding: "20px",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        marginTop: "12px",
      }}
    >
      <ResponsiveContainer width="100%" height={chartType === "pie" ? 300 : 350}>
        {chartType === "pie" ? (
          <PieChart>
            <Pie
              data={chartFormatData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={renderCustomLabel}
              outerRadius={100}
              fill="#8884d8"
              dataKey="value"
            >
              {chartFormatData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ color: "#ffffff", fontSize: "13px" }}
              iconType="circle"
            />
          </PieChart>
        ) : chartType === "bar" ? (
          <BarChart data={chartFormatData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
            <XAxis
              dataKey="year"
              stroke="rgba(255, 255, 255, 0.6)"
              style={{ fontSize: "12px" }}
            />
            <YAxis
              stroke="rgba(255, 255, 255, 0.6)"
              style={{ fontSize: "12px" }}
              tickFormatter={(value) => value.toLocaleString()}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ color: "#ffffff", fontSize: "13px" }}
              iconType="square"
            />
            {chartData.series.map((series, idx) => (
              <Bar
                key={series.label}
                dataKey={series.label}
                fill={COLORS[idx % COLORS.length]}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        ) : (
          <LineChart data={chartFormatData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
            <XAxis
              dataKey="year"
              stroke="rgba(255, 255, 255, 0.6)"
              style={{ fontSize: "12px" }}
            />
            <YAxis
              stroke="rgba(255, 255, 255, 0.6)"
              style={{ fontSize: "12px" }}
              tickFormatter={(value) => value.toLocaleString()}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ color: "#ffffff", fontSize: "13px" }}
              iconType="line"
            />
            {chartData.series.map((series, idx) => (
              <Line
                key={series.label}
                type="monotone"
                dataKey={series.label}
                stroke={COLORS[idx % COLORS.length]}
                strokeWidth={2}
                dot={{ fill: COLORS[idx % COLORS.length], r: 4 }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

