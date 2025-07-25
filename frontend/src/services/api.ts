import { WebSocketService, WebSocketMessage } from './websocketService';
import axios from 'axios';

/** the ChatAPI singleton class helps manage chat functionality through websocket connections
 * handles session creation, message sending, and websocket lifecycle management
 */
class ChatAPI {
  private static instance: ChatAPI;
  private webSocketService: WebSocketService | null = null;

  private constructor() {}

  static getInstance(): ChatAPI {
    if (!ChatAPI.instance) {
      ChatAPI.instance = new ChatAPI();
    }
    return ChatAPI.instance;
  }

  /** initializes websocket connection for a given user
   * only creates a new session if it doesn't exist already
   */
  async initializeWebSocket(userId: string): Promise<void> {
    try {
      if (!this.webSocketService || this.webSocketService.getSessionId() === null) {
        this.webSocketService = new WebSocketService(userId);
        await this.webSocketService.connect();
        console.log('WebSocket initialized successfully for user:', userId);
      }
    } catch (error) {
      console.error('WebSocket initialization error:', error);
      throw error;
    }
  }

  /** creates new chat session for the user
   * establishes new websocket connection and retrieves session id
   * falls back to HTTP API if websocket is websocket session id is unavailable
   */
  async createNewSession(userId: string): Promise<string> {
    try {
      // create a new WebSocketService instance for a new session
      this.webSocketService = new WebSocketService(userId);
      await this.webSocketService.connect();
      
      // wait briefly to ensure session_id is received
      const maxWaitTime = 5000; // 5 seconds
      const startTime = Date.now();
      while (!this.webSocketService.getSessionId() && Date.now() - startTime < maxWaitTime) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      const sessionId = this.webSocketService.getSessionId();
      if (sessionId) {
        console.log('Session ID from WebSocket:', sessionId);
        return sessionId;
      }

      console.warn('No session ID from WebSocket, falling back to HTTP');
      const response = await axios.post('http://localhost:8500/create_session', { user_id: userId });
      if (response.data.session_id) {
        console.log('Session ID from HTTP:', response.data.session_id);
        return response.data.session_id;
      }
      throw new Error('No session ID received from HTTP endpoint');
    } catch (error) {
      console.error('Error creating new session:', error);
      throw error;
    }
  }

  /** send message through websocket connection 
   * initialize websocket if it's not already connected
   */
  async sendMessage(message: string, userId: string): Promise<WebSocketMessage> {
    try {
      if (!this.webSocketService) {
        await this.initializeWebSocket(userId);
      }
      const response = await this.webSocketService!.sendMessage(message);
      return { response };
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }

  // retrieve current session info
  getSessionInfo(): { sessionId: string | null } {
    return {
      sessionId: this.webSocketService ? this.webSocketService.getSessionId() : null,
    };
  }

  // cleans up websocket connection and resets service instance
  // should only be called when chat session is no longer needed
  cleanup(): void {
    if (this.webSocketService) {
      this.webSocketService.disconnect();
      this.webSocketService = null;
      console.log('WebSocket cleaned up');
    }
  }
}

// export singleton instance for use through the application 
export const chatAPI = ChatAPI.getInstance();
