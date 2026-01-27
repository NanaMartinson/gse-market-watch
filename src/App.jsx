import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ArrowUp, ArrowDown, Download, Search, RefreshCw, TrendingUp, Activity, Info } from 'lucide-react';

// --- CONFIG ---
// Ghana 91-day T-bill rate (update periodically)
const RISK_FREE_RATE = 0.111969; // 11.20% annualized (Jan 2026 GH 91-day T-bill)

// --- COMPONENTS ---
const Card = ({ children, className = "" }) => (
  <div className={`bg-slate-800 rounded-lg border border-slate-700 ${className}`}>
    {children}
  </div>
);

const Badge = ({ change, changePercent }) => {
  const isPositive = (change || 0) >= 0;
  const pct = changePercent !== undefined ? changePercent : 0;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
      isPositive 
        ? 'bg-green-900/30 text-green-400' 
        : 'bg-red-900/30 text-red-400'
    }`}>
      {isPositive ? <ArrowUp className="w-3 h-3 mr-1" /> : <ArrowDown className="w-3 h-3 mr-1" />}
      {Math.abs(pct).toFixed(2)}%
    </span>
  );
};

const MetricCard = ({ label, value, subValue, tooltip }) => (
  <Card className="p-4 relative group">
    <div className="flex items-center gap-1 text-slate-400 text-xs mb-1">
      {label}
      {tooltip && (
        <div className="relative">
          <Info className="w-3 h-3 cursor-help" />
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-700 text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
            {tooltip}
          </div>
        </div>
      )}
    </div>
    <div className="font-semibold text-white">{value}</div>
    {subValue && <div className="text-xs text-slate-500 mt-1">{subValue}</div>}
  </Card>
);

const PerformanceCard = ({ label, value }) => {
  const isNA = value === null || value === undefined;
  const isPositive = !isNA && value >= 0;
  
  return (
    <Card className="p-4 text-center">
      <div className="text-slate-400 text-xs mb-1">{label}</div>
      <div className={`font-semibold ${
        isNA ? 'text-slate-500' :
        isPositive ? 'text-green-400' : 'text-red-400'
      }`}>
        {isNA ? 'N/A' : `${isPositive ? '+' : ''}${value.toFixed(2)}%`}
      </div>
    </Card>
  );
};

export default function GSEApp() {
  const [marketData, setMarketData] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [lastUpdated, setLastUpdated] = useState("Loading...");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [timeRange, setTimeRange] = useState("1Y");

  // --- DATA FETCHING ---
  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('/gse_data.json');
        
        if (!res.ok) {
           throw new Error("Data file not found");
        }
        
        const data = await res.json();
        
        if (!data.stocks || !Array.isArray(data.stocks)) {
            throw new Error("Invalid JSON format");
        }

        setMarketData(data.stocks);
        setLastUpdated(data.last_updated || new Date().toLocaleDateString());
        
        if (data.stocks.length > 0) {
           setSelectedStock(data.stocks[0]);
        }
        setLoading(false);

      } catch (err) {
        console.warn("Market Data Load Status:", err.message);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Filter history by time range
  const getFilteredHistory = (stock) => {
    if (!stock?.history) return [];
    
    const history = stock.history;
    
    // Handle YTD separately
    if (timeRange === "YTD") {
      const currentYear = new Date().getFullYear();
      return history.filter(h => {
        const year = new Date(h.date).getFullYear();
        return year === currentYear;
      });
    }
    
    const ranges = {
      "1M": 21,
      "3M": 63,
      "6M": 126,
      "1Y": 252,
      "5Y": 1260,
      "ALL": history.length
    };
    
    const days = ranges[timeRange] || history.length;
    return history.slice(-days);
  };

  const downloadCSV = () => {
    if (!selectedStock) return;
    const headers = ["Date", "Symbol", "Price (GHS)", "Change", "Change %", "Volume"];
    const rows = (selectedStock.history || []).map(row => [
      row.date, 
      selectedStock.symbol, 
      row.close, 
      row.change || 0, 
      row.changePercent || 0,
      row.volume || 0
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + headers.join(",") + "\n" + rows.map(e => e.join(",")).join("\n");
    const link = document.createElement("a");
    link.href = encodeURI(csvContent);
    link.download = `${selectedStock.symbol}_GSE_Data.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredStocks = marketData.filter(stock => 
    (stock.symbol && stock.symbol.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (stock.name && stock.name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Calculate metrics
  const getMetrics = (stock) => {
    if (!stock) return {};
    
    const history = stock.history || [];
    const prices = history.map(h => h.close).filter(p => p > 0);
    
    if (prices.length < 2) return {};
    
    // Moving averages
    const ma20 = prices.length >= 20 
      ? prices.slice(-20).reduce((a, b) => a + b, 0) / 20 
      : null;
    const ma50 = prices.length >= 50 
      ? prices.slice(-50).reduce((a, b) => a + b, 0) / 50 
      : null;
    
    // Calculate daily returns
    const dailyReturns = [];
    for (let i = 1; i < prices.length; i++) {
      if (prices[i-1] > 0) {
        dailyReturns.push((prices[i] - prices[i-1]) / prices[i-1]);
      }
    }
    
    // Volatility (annualized standard deviation of returns)
    let volatility = null;
    let sharpeRatio = null;
    
    if (dailyReturns.length >= 20) {
      const recentReturns = dailyReturns.slice(-30); // Last 30 trading days
      const mean = recentReturns.reduce((a, b) => a + b, 0) / recentReturns.length;
      const variance = recentReturns.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / recentReturns.length;
      const dailyVol = Math.sqrt(variance);
      volatility = dailyVol * Math.sqrt(252) * 100; // Annualized as percentage
      
      // Sharpe Ratio: (Annualized Return - Risk Free Rate) / Annualized Volatility
      if (volatility > 0) {
        const annualizedReturn = mean * 252; // Annualized mean return
        sharpeRatio = (annualizedReturn - RISK_FREE_RATE) / (volatility / 100);
      }
    }
    
    // Period returns
    const getReturn = (days) => {
      if (prices.length < days + 1) return null;
      const oldPrice = prices[prices.length - days - 1];
      const newPrice = prices[prices.length - 1];
      if (oldPrice <= 0) return null;
      return ((newPrice - oldPrice) / oldPrice) * 100;
    };
    
    // YTD return - find first trading day of current year
    let ytdReturn = null;
    if (history.length > 0) {
      const currentYear = new Date().getFullYear();
      const ytdHistory = history.filter(h => {
        const d = new Date(h.date);
        return d.getFullYear() === currentYear;
      });
      
      if (ytdHistory.length > 1) {
        const firstPrice = ytdHistory[0].close;
        const lastPrice = ytdHistory[ytdHistory.length - 1].close;
        if (firstPrice > 0) {
          ytdReturn = ((lastPrice - firstPrice) / firstPrice) * 100;
        }
      }
    }
    
    return {
      ma20,
      ma50,
      volatility,
      sharpeRatio,
      return1W: getReturn(5),
      return1M: getReturn(21),
      return3M: getReturn(63),
      return6M: getReturn(126),
      return1Y: getReturn(252),
      ytdReturn
    };
  };

  // --- LOADING STATE ---
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 text-slate-500">
        <RefreshCw className="w-6 h-6 animate-spin mr-2" /> Initializing...
    </div>
  );

  // --- ERROR / EMPTY STATE ---
  if (error || marketData.length === 0) return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center bg-slate-900 text-slate-100">
        <div className="bg-yellow-900/30 p-4 rounded-full mb-4">
            <Activity className="w-10 h-10 text-yellow-400" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Ready to Load Data</h2>
        <p className="text-slate-400 max-w-md mb-8">
            The dashboard is ready, but it cannot find the <code className="bg-slate-800 px-1 rounded">gse_data.json</code> file yet.
        </p>
        
        <Card className="p-6 max-w-lg w-full text-left">
            <h3 className="font-bold border-b border-slate-700 pb-2 mb-4">Next Steps:</h3>
            <ol className="list-decimal list-inside space-y-3 text-sm text-slate-300">
                <li>Run <code className="bg-slate-700 px-1 rounded">python scripts/build_data.py</code> to generate the JSON file</li>
                <li>Or wait for the GitHub Action to run automatically</li>
                <li>Refresh this page once the data is generated</li>
            </ol>
        </Card>
        
        <button onClick={() => window.location.reload()} className="mt-8 px-6 py-2 bg-yellow-500 hover:bg-yellow-600 text-slate-900 rounded-full font-medium transition-colors">
            Check Again
        </button>
    </div>
  );

  if (!selectedStock) return null;

  const metrics = getMetrics(selectedStock);
  const filteredHistory = getFilteredHistory(selectedStock);

  // --- MAIN DASHBOARD ---
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans">
      {/* Navigation */}
      <nav className="bg-slate-800 border-b border-slate-700 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
             <div className="bg-yellow-500 p-2 rounded-lg">
               <TrendingUp className="h-6 w-6 text-slate-900" />
             </div>
             <div>
                <h1 className="text-xl font-bold">GSE Market Watch</h1>
                <p className="text-xs text-slate-400">Data as of {lastUpdated}</p>
             </div>
          </div>
          <div className="text-xs text-slate-500">
            Risk-free rate: {(RISK_FREE_RATE * 100).toFixed(0)}% (91-day T-bill)
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar - Stock List */}
        <div className="lg:col-span-1 space-y-4">
           {/* Search */}
           <Card className="p-2 flex items-center gap-2">
              <Search className="w-5 h-5 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search stocks..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-transparent border-none focus:outline-none w-full text-sm placeholder-slate-500" 
              />
           </Card>
           
           {/* Stock List */}
           <Card className="overflow-hidden max-h-[600px] overflow-y-auto">
              {filteredStocks.map(stock => (
                 <div 
                   key={stock.symbol} 
                   onClick={() => setSelectedStock(stock)} 
                   className={`p-4 cursor-pointer border-b border-slate-700 last:border-0 hover:bg-slate-700/50 transition-colors ${
                     selectedStock?.symbol === stock.symbol ? 'bg-slate-700' : ''
                   }`}
                 >
                    <div className="flex justify-between items-start">
                      <div>
                         <div className="font-bold text-white">{stock.symbol}</div>
                         <div className="text-xs text-slate-400 truncate max-w-[120px]">{stock.name}</div>
                      </div>
                      <div className="text-right">
                         <div className="font-mono text-white">{stock.price?.toFixed(2)}</div>
                         <Badge change={stock.change} changePercent={stock.changePercent} />
                      </div>
                    </div>
                 </div>
              ))}
           </Card>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3 space-y-6">
           {/* Stock Header */}
           <Card className="p-6">
              <div className="flex justify-between items-start mb-6">
                 <div>
                    <h2 className="text-2xl font-bold text-white">{selectedStock.name}</h2>
                    <div className="text-sm text-slate-400">
                      {selectedStock.symbol} • {selectedStock.sector || 'General'}
                    </div>
                 </div>
                 <div className="text-right">
                    <div className="text-4xl font-bold font-mono text-white">
                      GH₵ {selectedStock.price?.toFixed(2)}
                    </div>
                    <div className={`text-sm font-medium ${
                      (selectedStock.change || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                       {(selectedStock.change || 0) >= 0 ? '▲' : '▼'} {Math.abs(selectedStock.change || 0).toFixed(2)} ({(selectedStock.changePercent || 0) >= 0 ? '+' : ''}{(selectedStock.changePercent || 0).toFixed(2)}%)
                    </div>
                 </div>
              </div>

              {/* Time Range Selector */}
              <div className="flex gap-2 mb-4 flex-wrap">
                {["1M", "3M", "6M", "YTD", "1Y", "5Y", "ALL"].map(range => (
                  <button
                    key={range}
                    onClick={() => setTimeRange(range)}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      timeRange === range 
                        ? 'bg-yellow-500 text-slate-900' 
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    {range}
                  </button>
                ))}
              </div>

              {/* Price Chart */}
              <div className="h-[300px] w-full">
                 <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={filteredHistory}>
                       <defs>
                          <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                             <stop offset="5%" stopColor="#eab308" stopOpacity={0.3}/>
                             <stop offset="95%" stopColor="#eab308" stopOpacity={0}/>
                          </linearGradient>
                       </defs>
                       <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" />
                       <XAxis 
                         dataKey="date" 
                         tick={{fill: '#94a3b8', fontSize: 11}} 
                         tickFormatter={(val) => {
                           const d = new Date(val);
                           return d.toLocaleDateString('en-GB', { month: 'short', year: '2-digit' });
                         }}
                         interval="preserveStartEnd"
                       />
                       <YAxis 
                         domain={['auto', 'auto']} 
                         orientation="right" 
                         tick={{fill: '#94a3b8', fontSize: 11}}
                         tickFormatter={(val) => `₵${val}`}
                       />
                       <Tooltip 
                         contentStyle={{
                           backgroundColor: '#1e293b', 
                           border: '1px solid #334155',
                           borderRadius: '8px'
                         }}
                         labelFormatter={(val) => new Date(val).toLocaleDateString('en-GB', { 
                           day: 'numeric', month: 'short', year: 'numeric' 
                         })}
                         formatter={(val) => [`GH₵ ${Number(val).toFixed(2)}`, 'Price']}
                       />
                       <Area 
                         type="monotone" 
                         dataKey="close" 
                         stroke="#eab308" 
                         strokeWidth={2}
                         fill="url(#colorPrice)" 
                       />
                    </AreaChart>
                 </ResponsiveContainer>
              </div>

              {/* Download Button */}
              <div className="mt-4 flex justify-end">
                 <button 
                   onClick={downloadCSV} 
                   className="flex items-center gap-2 text-sm bg-slate-700 px-4 py-2 rounded hover:bg-slate-600 transition-colors"
                 >
                    <Download className="w-4 h-4" /> Download CSV
                 </button>
              </div>
           </Card>

           {/* Key Statistics */}
           <div>
             <h3 className="text-lg font-semibold mb-4 text-slate-300">Key Statistics</h3>
             <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard label="Previous Close" value={`GH₵ ${selectedStock.prevClose?.toFixed(2) || 'N/A'}`} />
                <MetricCard label="52-Week High" value={`GH₵ ${selectedStock.yearHigh?.toFixed(2) || 'N/A'}`} />
                <MetricCard label="52-Week Low" value={`GH₵ ${selectedStock.yearLow?.toFixed(2) || 'N/A'}`} />
                <MetricCard label="Volume" value={selectedStock.volume?.toLocaleString() || '0'} />
                <MetricCard label="Avg Vol (10d)" value={selectedStock.avgVolume10d?.toLocaleString() || '0'} />
                <MetricCard label="Avg Vol (30d)" value={selectedStock.avgVolume30d?.toLocaleString() || '0'} />
                <MetricCard label="20-Day MA" value={metrics.ma20 ? `GH₵ ${metrics.ma20.toFixed(2)}` : 'N/A'} />
                <MetricCard label="50-Day MA" value={metrics.ma50 ? `GH₵ ${metrics.ma50.toFixed(2)}` : 'N/A'} />
             </div>
           </div>

           {/* Risk Metrics */}
           <div>
             <h3 className="text-lg font-semibold mb-4 text-slate-300">Risk Metrics</h3>
             <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard 
                  label="Volatility (30d)" 
                  value={metrics.volatility ? `${metrics.volatility.toFixed(2)}%` : 'N/A'} 
                  tooltip="Annualized standard deviation of daily returns"
                />
                <MetricCard 
                  label="Sharpe Ratio" 
                  value={metrics.sharpeRatio !== null && metrics.sharpeRatio !== undefined ? metrics.sharpeRatio.toFixed(2) : 'N/A'} 
                  tooltip={`Risk-adjusted return (using ${(RISK_FREE_RATE * 100).toFixed(0)}% T-bill rate)`}
                />
                <MetricCard 
                  label="Daily Change" 
                  value={`${(selectedStock.changePercent || 0) >= 0 ? '+' : ''}${(selectedStock.changePercent || 0).toFixed(2)}%`}
                />
                <MetricCard 
                  label="Price vs 50-MA" 
                  value={metrics.ma50 ? `${((selectedStock.price / metrics.ma50 - 1) * 100).toFixed(2)}%` : 'N/A'}
                  tooltip="Current price relative to 50-day moving average"
                />
             </div>
           </div>

           {/* Performance */}
           <div>
             <h3 className="text-lg font-semibold mb-4 text-slate-300">Performance</h3>
             <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
                <PerformanceCard label="1 Week" value={metrics.return1W} />
                <PerformanceCard label="1 Month" value={metrics.return1M} />
                <PerformanceCard label="3 Months" value={metrics.return3M} />
                <PerformanceCard label="6 Months" value={metrics.return6M} />
                <PerformanceCard label="1 Year" value={metrics.return1Y} />
                <PerformanceCard label="YTD" value={metrics.ytdReturn} />
             </div>
           </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 mt-12 py-6 text-center text-slate-500 text-sm">
        GSE Market Watch • Data sourced from Ghana Stock Exchange • Risk-free rate: Ghana 91-day T-bill
      </footer>
    </div>
  );
}
