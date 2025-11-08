// src/lib/api.ts
const API_BASE_URL = 'http://localhost:5000/api';

class ApiClient {
  private async request(endpoint: string, options: RequestInit = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      credentials: 'include', // Important for session cookies
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || 'Request failed');
    }

    return response.json();
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
}

export const api = new ApiClient();
