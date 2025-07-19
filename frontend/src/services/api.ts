// this code is a helper module that makes it easy to connect our React frontend with FastAPI
// uses a library called axios to send and receive HTTP requests
// sets up a way for React App to send chat messages to the backend and receive the AI responses
// organizes our code such that all requests occur in one place

import axios from 'axios'; // talks to server to get/send data , basically letting your frontend talk to the backend

const API_BASE_URL = 'http://localhost:8000'; // Your FastAPI backend URL

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout for AI responses
});

export interface ChatRequest {
  query: string;
  username: string;
}

export interface ChatResponse {
  response: string;
}

export const chatAPI = {
  sendMessage: async (query: string, username: string): Promise<ChatResponse> => {
    try {
      const response = await api.post<ChatResponse>('/chat', {
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
  }
};

export default api;