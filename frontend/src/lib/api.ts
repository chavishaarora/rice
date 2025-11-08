// src/lib/api.ts
const API_BASE_URL = 'http://localhost:5001/api';

class ApiClient {
  private async request(endpoint: string, options: RequestInit = {}) {
    try {
      console.log(`Making ${options.method || 'GET'} request to: ${API_BASE_URL}${endpoint}`);
      
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        credentials: 'include', // Important for session cookies
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      console.log(`Response status: ${response.status}`);

      // Try to parse JSON response
      let data;
      try {
        data = await response.json();
      } catch (e) {
        console.error('Failed to parse JSON response:', e);
        throw new Error('Invalid response from server');
      }

      if (!response.ok) {
        const error = data?.error || `Request failed with status ${response.status}`;
        console.error('API Error:', error);
        throw new Error(error);
      }

      return data;
    } catch (error) {
      console.error('API request failed:', error);
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Network request failed');
    }
  }

  // Auth endpoints
  async signup(email: string, password: string, fullName: string) {
    return this.request('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password, fullName }),
    });
  }

  async login(email: string, password: string) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async logout() {
    return this.request('/auth/logout', {
      method: 'POST',
    });
  }

  async getUser() {
    return this.request('/auth/user');
  }

  // Profile endpoints
  async getProfile() {
    return this.request('/profile');
  }

  async updateProfile(profileData: any) {
    return this.request('/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData),
    });
  }

  // Conversation endpoints
  async createConversation() {
    return this.request('/conversations', {
      method: 'POST',
    });
  }

  async sendMessage(conversationId: string, messages: any[]) {
    return this.request('/travel-chat', {
      method: 'POST',
      body: JSON.stringify({ conversationId, messages }),
    });
  }

  async getSuggestions(conversationId: string) {
    return this.request(`/suggestions/${conversationId}`);
  }

  // Health check endpoint
  async healthCheck() {
    return this.request('/health');
  }
}

export const api = new ApiClient();
