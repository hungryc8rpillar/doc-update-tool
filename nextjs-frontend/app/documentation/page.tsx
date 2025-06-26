'use client';

import { useState } from 'react';
import { Search, FileText, Brain, CheckCircle, XCircle } from 'lucide-react';
import { api, AnalyzeResponse } from '@/lib/api';
import Link from 'next/link';


export default function DocumentationPage() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    
    try {
      const response = await api.analyzeAndSave(query);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const clearResults = () => {
    setResult(null);
    setError(null);
    setQuery('');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <FileText className="h-8 w-8 text-blue-600 mr-3" />
                <div>
                  <h1 className="text-3xl font-bold text-gray-900">
                    Documentation Update Tool
                  </h1>
                  <p className="mt-1 text-gray-600">
                    AI-powered documentation analysis and update suggestions
                  </p>
                </div>
              </div>
              <div className="flex space-x-3">
                <a 
                  href="http://localhost:8000/docs" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  API Docs
                </a>
                <button
                  onClick={clearResults}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Main Form */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-8">
          <div className="flex items-center mb-4">
            <Brain className="h-6 w-6 text-purple-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">
              Analyze Documentation Changes
            </h2>
          </div>
          
          <form onSubmit={handleAnalyze} className="space-y-4">
            <div>
              <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
                Describe the changes you want to make:
              </label>
              <textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g., We don't support agents as_tool anymore, other agents should only be invoked via handoff"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                rows={4}
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                Be specific about what functionality is changing and how it should be updated in the documentation.
              </p>
            </div>
            
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="inline-flex items-center px-6 py-3 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Analyzing with AI...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Analyze & Generate Suggestions
                </>
              )}
            </button>
          </form>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-8">
            <div className="flex items-center">
              <XCircle className="h-5 w-5 text-red-400 mr-2" />
              <div className="text-red-800">
                <strong>Error:</strong> {error}
              </div>
            </div>
          </div>
        )}

        {/* Results Display */}
        {result && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <div className="flex items-center">
                  <CheckCircle className="h-6 w-6 text-green-500 mr-2" />
                  <h3 className="text-lg font-semibold text-gray-900">
                    Analysis Complete
                  </h3>
                </div>
                <div className="mt-1 text-sm text-gray-600">
                  <span className="font-medium">Batch ID:</span> {result.batch_id}
                  <span className="mx-2">•</span>
                  <span className="font-medium">{result.suggestions_count}</span> suggestion{result.suggestions_count !== 1 ? 's' : ''} generated
                </div>
              </div>
              <div className="text-sm text-green-600 bg-green-50 px-3 py-1 rounded-full font-medium">
                {(result.status ? result.status.replace('_', ' ').toUpperCase() : 'UNKNOWN')}
              </div>
            </div>

            {/* Query Display */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Original Query:</h4>
              <p className="text-sm text-gray-900 italic">"{result.query}"</p>
            </div>

            {/* Suggestions */}
            <div className="space-y-6">
              {(result.suggestions || []).map((suggestion, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-5 hover:shadow-sm transition-shadow">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-semibold text-gray-900 text-lg">
                      Suggestion {index + 1}
                    </h4>
                    <div className="flex items-center space-x-3">
                      <span className="text-xs text-gray-500 uppercase tracking-wide">
                        {suggestion.change_type}
                      </span>
                      <div className={`text-xs px-3 py-1 rounded-full font-medium ${
                        suggestion.confidence_score > 0.8 
                          ? 'bg-green-100 text-green-800'
                          : suggestion.confidence_score > 0.6
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {Math.round(suggestion.confidence_score * 100)}% confidence
                      </div>
                    </div>
                  </div>

                  {/* File Information */}
                  <div className="mb-4 bg-gray-50 border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center space-x-4 text-sm">
                      <div>
                        <span className="font-medium text-gray-700">Section:</span>
                        <span className="ml-1 text-gray-900">{suggestion.section_title}</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">File:</span>
                        <span className="ml-1 text-gray-900 font-mono text-xs">
                          {suggestion.file_path.split('/').pop() || suggestion.file_path}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <h5 className="text-sm font-medium text-gray-700 mb-2">AI Reasoning:</h5>
                      <p className="text-sm text-gray-600 bg-blue-50 p-3 rounded border-l-4 border-blue-200">
                        {suggestion.reasoning}
                      </p>
                    </div>

                    <div className="grid lg:grid-cols-2 gap-4">
                      <div>
                        <h5 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                          <span className="w-3 h-3 bg-red-400 rounded-full mr-2"></span>
                          Current Content:
                        </h5>
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-gray-800 font-mono text-xs leading-relaxed max-h-48 overflow-y-auto">
                          {suggestion.original_content}
                        </div>
                      </div>
                      
                      <div>
                        <h5 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                          <span className="w-3 h-3 bg-green-400 rounded-full mr-2"></span>
                          Suggested Content:
                        </h5>
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-gray-800 font-mono text-xs leading-relaxed max-h-48 overflow-y-auto">
                          {suggestion.suggested_content}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Actions */}
            <div className="mt-8 flex justify-center space-x-4">
              <button
                onClick={clearResults}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Analyze Another Query
              </button>
              <Link
                href="/documentation/review"
                className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
               >
                <CheckCircle className="h-4 w-4 mr-2" />
                Review & Approve Changes
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
