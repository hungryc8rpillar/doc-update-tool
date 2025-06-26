'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Edit3, Clock, ArrowLeft, BarChart3 } from 'lucide-react';
import { api } from '@/lib/api';
import Link from 'next/link';

interface PendingBatch {
  batch_id: string;
  query: string;
  user_id: string;
  created_at: string;
  status: string;
  suggestions: PendingSuggestion[];
}

interface PendingSuggestion {
  suggestion_id: string;
  section_id: string;
  section_title: string;
  file_path: string;
  original_content: string;
  suggested_content: string;
  change_type: string;
  confidence_score: number;
  reasoning: string;
  status: string;
}

interface Statistics {
  pending_suggestions: number;
  applied_suggestions: number;
  total_suggestions: number;
  pending_batches: number;
  applied_batches: number;
}

export default function ReviewPage() {
  const [pendingBatches, setPendingBatches] = useState<PendingBatch[]>([]);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<string>>(new Set());
  const [editingContent, setEditingContent] = useState<{ [key: string]: string }>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [pendingResponse, statsResponse] = await Promise.all([
        api.getPendingUpdates(),
        api.getStatistics()
      ]);
      
      setPendingBatches(pendingResponse.pending_updates || []);
      setStatistics(statsResponse);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSuggestion = (suggestionId: string, checked: boolean) => {
    const newSelected = new Set(selectedSuggestions);
    if (checked) {
      newSelected.add(suggestionId);
    } else {
      newSelected.delete(suggestionId);
    }
    setSelectedSuggestions(newSelected);
  };

  const handleSelectAllForBatch = (batchId: string, checked: boolean) => {
    const batch = pendingBatches.find(b => b.batch_id === batchId);
    if (!batch) return;

    const newSelected = new Set(selectedSuggestions);
    batch.suggestions.forEach(suggestion => {
      if (suggestion.status === 'pending') {
        if (checked) {
          newSelected.add(suggestion.suggestion_id);
        } else {
          newSelected.delete(suggestion.suggestion_id);
        }
      }
    });
    setSelectedSuggestions(newSelected);
  };

  const handleEditContent = (suggestionId: string, content: string) => {
    setEditingContent(prev => ({
      ...prev,
      [suggestionId]: content
    }));
  };

  const handleApproveSelected = async () => {
    if (selectedSuggestions.size === 0) return;

    const batchGroups: { [batchId: string]: string[] } = {};
    
    // Group suggestions by batch
    pendingBatches.forEach(batch => {
      batch.suggestions.forEach(suggestion => {
        if (selectedSuggestions.has(suggestion.suggestion_id)) {
          if (!batchGroups[batch.batch_id]) {
            batchGroups[batch.batch_id] = [];
          }
          batchGroups[batch.batch_id].push(suggestion.suggestion_id);
        }
      });
    });

    setProcessing('approving');

    try {
      // Approve suggestions for each batch
      for (const [batchId, suggestionIds] of Object.entries(batchGroups)) {
        await api.approveSuggestions(batchId, suggestionIds);
      }
      
      setSelectedSuggestions(new Set());
      setEditingContent({});
      await loadData(); // Reload data
    } catch (error) {
      console.error('Failed to approve suggestions:', error);
      alert('Failed to approve suggestions. Please try again.');
    } finally {
      setProcessing(null);
    }
  };

  const handleRejectSelected = async () => {
    if (selectedSuggestions.size === 0) return;

    const batchGroups: { [batchId: string]: string[] } = {};
    
    // Group suggestions by batch
    pendingBatches.forEach(batch => {
      batch.suggestions.forEach(suggestion => {
        if (selectedSuggestions.has(suggestion.suggestion_id)) {
          if (!batchGroups[batch.batch_id]) {
            batchGroups[batch.batch_id] = [];
          }
          batchGroups[batch.batch_id].push(suggestion.suggestion_id);
        }
      });
    });

    setProcessing('rejecting');

    try {
      // Reject suggestions for each batch
      for (const [batchId, suggestionIds] of Object.entries(batchGroups)) {
        await api.rejectSuggestions(batchId, suggestionIds);
      }
      
      setSelectedSuggestions(new Set());
      await loadData(); // Reload data
    } catch (error) {
      console.error('Failed to reject suggestions:', error);
      alert('Failed to reject suggestions. Please try again.');
    } finally {
      setProcessing(null);
    }
  };

  const handleRevertAll = async () => {
    if (!confirm('Are you sure you want to revert all applied changes? This action cannot be undone.')) {
      return;
    }

    setProcessing('reverting');
    try {
      const result = await api.revertAllUpdates();
      alert(
        `Revert process finished.\n\n` +
        `Reverted and Removed: ${result.reverted_and_removed_count}\n` +
        `Failed to Revert: ${result.failed_to_revert_count}`
      );
      await loadData(); // Reload data to reflect changes
    } catch (error) {
      console.error('Failed to revert updates:', error);
      alert('An error occurred while reverting updates. Please check the console for details.');
    } finally {
      setProcessing(null);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getBatchPendingCount = (batch: PendingBatch) => {
    return batch.suggestions.filter(s => s.status === 'pending').length;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading review data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <Link 
                  href="/documentation"
                  className="mr-4 p-2 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <ArrowLeft className="h-5 w-5" />
                </Link>
                <div className="flex items-center">
                  <BarChart3 className="h-8 w-8 text-green-600 mr-3" />
                  <div>
                    <h1 className="text-3xl font-bold text-gray-900">
                      Review & Approve Changes
                    </h1>
                    <p className="mt-1 text-gray-600">
                      Review AI suggestions and approve documentation updates
                    </p>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <Link
                  href="/documentation/history"
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border rounded-md hover:bg-gray-50"
                >
                  History
                </Link>
                <button
                  onClick={handleRevertAll}
                  disabled={processing !== null}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 disabled:bg-red-300"
                >
                  {processing === 'reverting' ? 'Reverting...' : 'Revert All Updates'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Statistics */}
        {statistics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow-sm border p-4">
              <div className="flex items-center">
                <Clock className="h-8 w-8 text-yellow-600" />
                <div className="ml-3">
                  <p className="text-2xl font-semibold text-gray-900">{statistics.pending_suggestions}</p>
                  <p className="text-sm text-gray-600">Pending Suggestions</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border p-4">
              <div className="flex items-center">
                <CheckCircle className="h-8 w-8 text-green-600" />
                <div className="ml-3">
                  <p className="text-2xl font-semibold text-gray-900">{statistics.applied_suggestions}</p>
                  <p className="text-sm text-gray-600">Applied Changes</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border p-4">
              <div className="flex items-center">
                <BarChart3 className="h-8 w-8 text-blue-600" />
                <div className="ml-3">
                  <p className="text-2xl font-semibold text-gray-900">{statistics.total_suggestions}</p>
                  <p className="text-sm text-gray-600">Total Suggestions</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border p-4">
              <div className="flex items-center">
                <div className="h-8 w-8 bg-purple-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">
                  {statistics.pending_batches}
                </div>
                <div className="ml-3">
                  <p className="text-2xl font-semibold text-gray-900">{statistics.pending_batches}</p>
                  <p className="text-sm text-gray-600">Pending Batches</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Action Bar */}
        {selectedSuggestions.size > 0 && (
          <div className="bg-white rounded-lg shadow-sm border p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <p className="text-sm text-gray-700">
                  <span className="font-medium">{selectedSuggestions.size}</span> suggestion{selectedSuggestions.size !== 1 ? 's' : ''} selected
                </p>
              </div>
              <div className="flex space-x-3">
                <button
                  onClick={handleRejectSelected}
                  disabled={processing !== null}
                  className="inline-flex items-center px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                >
                  {processing === 'rejecting' ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600 mr-2"></div>
                  ) : (
                    <XCircle className="h-4 w-4 mr-2" />
                  )}
                  Reject Selected
                </button>
                <button
                  onClick={handleApproveSelected}
                  disabled={processing !== null}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                >
                  {processing === 'approving' ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  ) : (
                    <CheckCircle className="h-4 w-4 mr-2" />
                  )}
                  Approve Selected
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Pending Batches */}
        {pendingBatches.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border p-8 text-center">
            <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Pending Suggestions</h3>
            <p className="text-gray-600 mb-4">All suggestions have been reviewed and processed.</p>
            <Link 
              href="/documentation"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
            >
              Create New Analysis
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            {pendingBatches.map((batch) => {
              const pendingCount = getBatchPendingCount(batch);
              if (pendingCount === 0) return null;

              return (
                <div key={batch.batch_id} className="bg-white rounded-lg shadow-sm border">
                  {/* Batch Header */}
                  <div className="border-b border-gray-200 p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          Analysis Batch
                        </h3>
                        <div className="mt-1 text-sm text-gray-600">
                          <span className="font-medium">ID:</span> {batch.batch_id}
                          <span className="mx-2">•</span>
                          <span className="font-medium">Created:</span> {formatDate(batch.created_at)}
                          <span className="mx-2">•</span>
                          <span className="font-medium">{pendingCount}</span> pending suggestion{pendingCount !== 1 ? 's' : ''}
                        </div>
                        <div className="mt-2 p-3 bg-gray-50 rounded text-sm text-gray-800 italic">
                          "{batch.query}"
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={batch.suggestions
                              .filter(s => s.status === 'pending')
                              .every(s => selectedSuggestions.has(s.suggestion_id))}
                            onChange={(e) => handleSelectAllForBatch(batch.batch_id, e.target.checked)}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="ml-2 text-sm text-gray-700">Select All</span>
                        </label>
                      </div>
                    </div>
                  </div>

                  {/* Suggestions */}
                  <div className="divide-y divide-gray-200">
                    {batch.suggestions
                      .filter(suggestion => suggestion.status === 'pending')
                      .map((suggestion, index) => (
                      <div key={suggestion.suggestion_id} className="p-6">
                        <div className="flex items-start space-x-4">
                          <label className="flex items-center mt-1">
                            <input
                              type="checkbox"
                              checked={selectedSuggestions.has(suggestion.suggestion_id)}
                              onChange={(e) => handleSelectSuggestion(suggestion.suggestion_id, e.target.checked)}
                              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                          </label>

                          <div className="flex-1 space-y-4">
                            <div className="flex items-center justify-between">
                              <h4 className="font-medium text-gray-900">
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
                            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
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

                            <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded border-l-4 border-blue-200">
                              <strong>AI Reasoning:</strong> {suggestion.reasoning}
                            </div>

                            <div className="grid lg:grid-cols-2 gap-4">
                              <div>
                                <h5 className="text-sm font-medium text-gray-700 mb-2">Current Content:</h5>
                                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-gray-800 font-mono text-xs leading-relaxed max-h-32 overflow-y-auto">
                                  {suggestion.original_content}
                                </div>
                              </div>
                              
                              <div>
                                <div className="flex items-center justify-between mb-2">
                                  <h5 className="text-sm font-medium text-gray-700">Suggested Content:</h5>
                                  <button
                                    onClick={() => {
                                      const currentEdit = editingContent[suggestion.suggestion_id] || suggestion.suggested_content;
                                      const newContent = prompt('Edit suggestion:', currentEdit);
                                      if (newContent !== null) {
                                        handleEditContent(suggestion.suggestion_id, newContent);
                                      }
                                    }}
                                    className="text-xs text-blue-600 hover:text-blue-800 flex items-center"
                                  >
                                    <Edit3 className="h-3 w-3 mr-1" />
                                    Edit
                                  </button>
                                </div>
                                <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-gray-800 font-mono text-xs leading-relaxed max-h-32 overflow-y-auto">
                                  {editingContent[suggestion.suggestion_id] || suggestion.suggested_content}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}