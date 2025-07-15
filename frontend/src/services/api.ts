// services/api.ts
import axios from 'axios';
import { WebSocketService } from './websocketService';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export interface ChatRequest {
  query: string;
  username: string;
}

export interface ChatResponse {
  response: string;
}

// WebSocket service instance
let wsService: WebSocketService | null = null;
let wsConnected = false;

export const chatAPI = {
  // Initialize WebSocket connection
  initializeWebSocket: async (username: string): Promise<void> => {
    if (wsService) {
      wsService.disconnect();
    }
    
    wsService = new WebSocketService(username);
    try {
      await wsService.connect();
      wsConnected = true;
      console.log('WebSocket initialized successfully');
    } catch (error) {
      console.error('WebSocket initialization failed:', error);
      wsConnected = false;
    }
  },

  // Enhanced sendMessage with automatic fallback
  sendMessage: async (query: string, username: string): Promise<ChatResponse> => {
    // Try WebSocket first if connected
    if (wsService && wsConnected) {
      try {
        const response = await wsService.sendMessage(query);
        return { response };
      } catch (error) {
        console.warn('WebSocket failed, falling back to HTTP:', error);
        wsConnected = false;
      }
    }

    // Fallback to HTTP API
    try {
      const response = await api.post('/chat', {
        query,
        username
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

  // Get WebSocket session info
  getSessionInfo: () => ({
    connected: wsConnected,
    sessionId: wsService?.getSessionId() || null
  }),

  // Cleanup WebSocket
  cleanup: () => {
    if (wsService) {
      wsService.disconnect();
      wsService = null;
      wsConnected = false;
    }
  }
};

export default api;
