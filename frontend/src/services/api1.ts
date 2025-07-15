// // this code is a helper module that makes it easy to connect our React frontend with FastAPI
// // uses a library called axios to send and receive HTTP requests
// // sets up a way for React App to send chat messages to the backend and receive the AI responses
// // organizes our code such that all requests occur in one place

// import axios from 'axios'; // talks to server to get/send data , basically letting your frontend talk to the backend

// const API_BASE_URL = 'http://localhost:8000'; // Your FastAPI backend URL

// const api = axios.create({
//   baseURL: API_BASE_URL,
//   headers: {
//     'Content-Type': 'application/json',
//   },
//   timeout: 30000, // 30 second timeout for AI responses
// });

// export interface ChatRequest {
//   query: string;
//   username: string;
// }

// export interface ChatResponse {
//   response: string;
// }

// export const chatAPI = {
//   sendMessage: async (query: string, username: string): Promise<ChatResponse> => {
//     try {
//       const response = await api.post<ChatResponse>('/chat', {
//         query,
//         username
//       });
//       return response.data;
//     } catch (error) {
//       console.error('API Error:', error);
//       if (axios.isAxiosError(error)) {
//         throw new Error(error.response?.data?.detail || 'Failed to send message');
//       }
//       throw error;
//     }
//   }
// };

// export default api;

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';
const WS_BASE_URL = 'ws://localhost:8000/ws';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface ChatRequest {
  query: string;
  username: string;
}

export interface ChatResponse {
  response: string;
  session_id?: string;
}

export interface WebSocketMessage {
  session_id?: string;
  query?: string;
  response?: string;
  error?: string;
}

export interface ConversationHistory {
  query: string;
  response: string;
  timestamp: string;
}

export interface SessionData {
  session_id: string;
  conversation_history: ConversationHistory[];
}

export interface LoginResponse {
  token: string;
  user_id: string;
}

export const chatAPI = {
  // Authentication
  login: async (username: string): Promise<LoginResponse> => {
    try {
      const response = await api.post<LoginResponse>('/login', null, {
        params: { username }
      });
      
      // Store token for future requests
      localStorage.setItem('auth_token', response.data.token);
      
      return response.data;
    } catch (error) {
      console.error('Login Error:', error);
      throw new Error('Failed to login');
    }
  },

  // HTTP-based message sending (fallback)
  sendMessage: async (query: string, username: string): Promise<ChatResponse> => {
    try {
      const response = await api.post<ChatResponse>('/query', {
        query,
        username,
      });
      return response.data;
    } catch (error) {
      console.error('API Error:', error);
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to send message');
      }
      throw error;
    }
  },

  // Get session history
  getSessionHistory: async (sessionId: string): Promise<SessionData> => {
    try {
      const response = await api.get<SessionData>(`/session/${sessionId}/history`);
      return response.data;
    } catch (error) {
      console.error('Session History Error:', error);
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to get session history');
      }
      throw error;
    }
  },

  // WebSocket connection management
  createWebSocket: (
    userId: string,
    onMessage: (data: WebSocketMessage) => void,
    onError: (error: Event) => void,
    onClose: () => void,
    onOpen?: (sessionId: string) => void
  ): WebSocket => {
    const ws = new WebSocket(`${WS_BASE_URL}/${encodeURIComponent(userId)}`);

    ws.onopen = () => {
      console.log('WebSocket connected for user:', userId);
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        
        // Handle initial session_id message
        if (data.session_id && !data.query && !data.response && onOpen) {
          onOpen(data.session_id);
          return;
        }
        
        onMessage(data);
      } catch (error) {
        console.error('WebSocket message parse error:', error);
        onError(new Event('message_parse_error'));
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      onError(error);
    };

    ws.onclose = () => {
      console.log('WebSocket closed for user:', userId);
      onClose();
    };

    return ws;
  },

  // Utility to send a message via WebSocket
  sendWebSocketMessage: (ws: WebSocket, query: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ query }));
          resolve();
        } catch (error) {
          console.error('Failed to send WebSocket message:', error);
          reject(error);
        }
      } else {
        console.error('WebSocket is not open. Current state:', ws.readyState);
        reject(new Error('WebSocket is not open'));
      }
    });
  },

  // Check WebSocket connection status
  isWebSocketConnected: (ws: WebSocket): boolean => {
    return ws.readyState === WebSocket.OPEN;
  },

  // Close WebSocket connection
  closeWebSocket: (ws: WebSocket): void => {
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  },

  // Health check
  healthCheck: async (): Promise<{ status: string; redis: string }> => {
    try {
      const response = await api.get('/');
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }
};

export default api;