'use client';

import { useState } from 'react';
import { Send, Loader2, Sparkles, Clock, DollarSign, Cpu, ChevronDown, ChevronUp } from 'lucide-react';
import { generate, GenerateRequest, GenerateResponse, formatCost, formatLatency } from '@/lib/api';

const SAMPLE_TEXTS = {
  summarize: `The Industrial Revolution, which began in Britain in the late 18th century, marked a major turning point in human history. It transformed predominantly agrarian, rural societies in Europe and America into industrial and urban ones. New manufacturing processes led to the development of factories, and the introduction of machine tools changed the nature of work. The revolution also brought about improvements in transportation, including the development of steam-powered ships and railways, which facilitated the movement of goods and people on an unprecedented scale.`,
  sentiment: `I absolutely loved my experience at this restaurant! The food was incredible, the service was impeccable, and the atmosphere was perfect for a romantic dinner. The chef's special was a masterpiece of culinary art. I'll definitely be coming back and recommending this place to all my friends. Five stars isn't enough!`,
  rewrite: `The meeting was pretty bad. Nobody showed up on time and the presentation was boring. We didnt really accomplish anything useful and people kept checking their phones. I think we need to do better next time.`,
  chat: `What are the key differences between machine learning and deep learning? Can you explain when to use each approach?`,
  code: `Write a Python function that takes a list of numbers and returns the top 3 most frequent elements. Handle edge cases appropriately.`,
  analysis: `Our Q3 sales data shows: North region: $2.4M (up 15%), South region: $1.8M (down 5%), East region: $3.1M (up 22%), West region: $2.1M (flat). Total revenue: $9.4M. Customer acquisition cost increased by 8% while customer lifetime value grew by 12%.`,
};

const TASKS = [
  { value: 'summarize', label: 'Summarize', icon: '📝' },
  { value: 'sentiment', label: 'Sentiment', icon: '😊' },
  { value: 'rewrite', label: 'Rewrite', icon: '✏️' },
  { value: 'chat', label: 'Chat', icon: '💬' },
  { value: 'code', label: 'Code', icon: '💻' },
  { value: 'analysis', label: 'Analysis', icon: '📊' },
] as const;

const PREFERENCES = [
  { value: 'fast', label: 'Fast', description: 'Prioritize speed', icon: '⚡' },
  { value: 'cheap', label: 'Cheap', description: 'Minimize cost', icon: '💰' },
  { value: 'best', label: 'Best', description: 'Highest quality', icon: '🏆' },
  { value: 'balanced', label: 'Balanced', description: 'Optimize all', icon: '⚖️' },
] as const;

interface TryItDemoProps {
  onRequestComplete?: () => void;
}

export default function TryItDemo({ onRequestComplete }: TryItDemoProps) {
  const [task, setTask] = useState<GenerateRequest['task']>('summarize');
  const [preference, setPreference] = useState<GenerateRequest['model_preference']>('balanced');
  const [text, setText] = useState(SAMPLE_TEXTS.summarize);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const handleTaskChange = (newTask: GenerateRequest['task']) => {
    setTask(newTask);
    setText(SAMPLE_TEXTS[newTask]);
    setResponse(null);
    setError(null);
  };

  const handleSubmit = async () => {
    if (!text.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const result = await generate({
        task,
        model_preference: preference,
        text: text.trim(),
      });
      setResponse(result);
      onRequestComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate response');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-slate-100 bg-gradient-to-r from-primary-50 to-transparent">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-500 rounded-xl">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-800">Try It Live</h3>
            <p className="text-sm text-slate-500">Test the intelligent routing engine</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Task Selection */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-3">Task Type</label>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
            {TASKS.map((t) => (
              <button
                key={t.value}
                onClick={() => handleTaskChange(t.value)}
                className={`flex flex-col items-center gap-1 p-3 rounded-xl border-2 transition-all ${
                  task === t.value
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-slate-200 hover:border-slate-300 text-slate-600'
                }`}
              >
                <span className="text-xl">{t.icon}</span>
                <span className="text-xs font-medium">{t.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Preference Selection */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-3">Optimization Preference</label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {PREFERENCES.map((p) => (
              <button
                key={p.value}
                onClick={() => setPreference(p.value)}
                className={`flex items-center gap-2 p-3 rounded-xl border-2 transition-all ${
                  preference === p.value
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-slate-200 hover:border-slate-300 text-slate-600'
                }`}
              >
                <span className="text-lg">{p.icon}</span>
                <div className="text-left">
                  <p className="text-sm font-medium">{p.label}</p>
                  <p className="text-xs opacity-70">{p.description}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Text Input */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Input Text</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none transition-all"
            placeholder="Enter your text here..."
          />
        </div>

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={loading || !text.trim()}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white font-medium rounded-xl hover:from-primary-600 hover:to-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary-500/25"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Processing...</span>
            </>
          ) : (
            <>
              <Send className="w-5 h-5" />
              <span>Generate</span>
            </>
          )}
        </button>

        {/* Error Display */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Response Display */}
        {response && (
          <div className="space-y-4 animate-fade-in">
            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-xl">
                <Cpu className="w-5 h-5 text-primary-500" />
                <div>
                  <p className="text-xs text-slate-500">Model</p>
                  <p className="text-sm font-medium text-slate-700">
                    {response.routing.selected_model.split('/').pop()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-xl">
                <Clock className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-xs text-slate-500">Latency</p>
                  <p className="text-sm font-medium text-slate-700">
                    {formatLatency(response.performance.total_time_ms)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-xl">
                <DollarSign className="w-5 h-5 text-emerald-500" />
                <div>
                  <p className="text-xs text-slate-500">Cost</p>
                  <p className="text-sm font-medium text-slate-700">
                    {formatCost(response.usage.total_cost_usd)}
                  </p>
                </div>
              </div>
            </div>

            {/* Result */}
            <div className="p-4 bg-slate-50 rounded-xl">
              <p className="text-sm text-slate-500 mb-2">Result:</p>
              <p className="text-slate-700 whitespace-pre-wrap">{response.result}</p>
            </div>

            {/* Expandable Details */}
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
            >
              {showDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              {showDetails ? 'Hide' : 'Show'} routing details
            </button>

            {showDetails && (
              <div className="p-4 bg-slate-50 rounded-xl space-y-3 animate-fade-in">
                <div>
                  <p className="text-xs text-slate-500 mb-1">Routing Reason</p>
                  <p className="text-sm text-slate-700">{response.routing.reason}</p>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-xs text-slate-500">Cost Score</p>
                    <p className="text-sm font-medium">{(response.routing.cost_score * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Latency Score</p>
                    <p className="text-sm font-medium">{(response.routing.latency_score * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Quality Score</p>
                    <p className="text-sm font-medium">{(response.routing.quality_score * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Final Score</p>
                    <p className="text-sm font-medium">{(response.routing.final_score * 100).toFixed(0)}%</p>
                  </div>
                </div>
                {response.routing.alternatives_considered.length > 0 && (
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Alternatives Considered</p>
                    <div className="flex flex-wrap gap-2">
                      {response.routing.alternatives_considered.map((alt) => (
                        <span
                          key={alt}
                          className="px-2 py-1 text-xs bg-slate-200 text-slate-600 rounded-full"
                        >
                          {alt.split('/').pop()}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-4 pt-2 border-t border-slate-200">
                  <div>
                    <p className="text-xs text-slate-500">Input Tokens</p>
                    <p className="text-sm font-medium">{response.usage.input_tokens}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Output Tokens</p>
                    <p className="text-sm font-medium">{response.usage.output_tokens}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Provider</p>
                    <p className="text-sm font-medium capitalize">{response.routing.provider}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}