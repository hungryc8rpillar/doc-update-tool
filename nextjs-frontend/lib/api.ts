const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface DocumentSection {
  id: string;
  title: string;
  content: string;
  file_path: string;
  section_type: string;
  parent_section?: string;
}

export interface UpdateSuggestion {
  section_id: string;
  section_title: string;
  file_path: string;
  original_content: string;
  suggested_content: string;
  change_type: string;
  confidence_score: number;
  reasoning: string;
}

export interface AnalyzeResponse {
  batch_id: string;
  query: string;
  suggestions_count: number;
  suggestions: UpdateSuggestion[];
  status: string;
}

export const api = {
  // Health check
  async getHealth() {
    const response = await fetch(`${API_BASE}/api/documentation/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    return response.json();
  },

  // Analyze changes and save suggestions
  async analyzeAndSave(query: string): Promise<AnalyzeResponse> {
    const response = await fetch(`${API_BASE}/api/documentation/analyze-and-save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    return response.json();
  },

  // Get pending updates
  async getPendingUpdates(batchId?: string) {
    const url = batchId 
      ? `${API_BASE}/api/documentation/pending-updates?batch_id=${batchId}`
      : `${API_BASE}/api/documentation/pending-updates`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to get pending updates: ${response.status}`);
    }
    return response.json();
  },

  // Approve suggestions - FIXED VERSION
  async approveSuggestions(batchId: string, approvedIds: string[]) {
    console.log('Sending approve request:', { batchId, approvedIds });
    
    // batch_id as query parameter, approved_ids as object in request body
    const url = `${API_BASE}/api/documentation/approve-suggestions?batch_id=${encodeURIComponent(batchId)}`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved_ids: approvedIds }), // Send as object with approved_ids key
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Approve suggestions error:', response.status, errorText);
      throw new Error(`Failed to approve suggestions: ${response.status} - ${errorText}`);
    }
    
    return response.json();
  },

  // Reject suggestions - FIXED VERSION
  async rejectSuggestions(batchId: string, rejectedIds: string[]) {
    console.log('Sending reject request:', { batchId, rejectedIds });
    
    // batch_id as query parameter, rejected_ids as object in request body
    const url = `${API_BASE}/api/documentation/reject-suggestions?batch_id=${encodeURIComponent(batchId)}`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rejected_ids: rejectedIds }), // Send as object with rejected_ids key
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Reject suggestions error:', response.status, errorText);
      throw new Error(`Failed to reject suggestions: ${response.status} - ${errorText}`);
    }
    
    return response.json();
  },

  // Get statistics
  async getStatistics() {
    const response = await fetch(`${API_BASE}/api/documentation/update-statistics`);
    if (!response.ok) {
      throw new Error(`Failed to get statistics: ${response.status}`);
    }
    return response.json();
  },

  async revertAllUpdates() {
    const response = await fetch(`${API_BASE}/api/documentation/revert-all-updates`, {
      method: 'POST'
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to revert updates: ${response.status} - ${errorText}`);
    }
    return response.json();
  },

  async getAppliedUpdates() {
    const response = await fetch(`${API_BASE}/api/documentation/applied-updates`);
    if (!response.ok) {
      throw new Error(`Failed to get applied updates: ${response.status}`);
    }
    return response.json();
  }
};