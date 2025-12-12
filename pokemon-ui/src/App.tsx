import { useState, useEffect, useRef } from "react";
import "./styles/base.css";
import { PokemonStreamOverlay } from "./components/layout/PokemonStreamOverlay";
import type { PokemonGameState, LogEntry, Pokemon } from "./types/gameTypes";

const INITIAL_GAME_STATE: PokemonGameState = {
  badges: [],
  goals: {
    primary: "Loading...",
    secondary: "Loading...",
    tertiary: "Loading...",
  },
  otherGoals: "Loading...",
  minimapLocation: "Unknown Area",
  currentTeam: [],
  actions: 0,
  cycle: 0,
  gameStatus: "Connecting...",
  modelName: "N/A",
  tokensUsed: 0,
  minimapVisible: false,
  debugMode: false,
  currentCycleTime: 0,
  prevCycleTime: 0,
  avgCycleTime: 0,
};

// TTS Commentary with duration for synced typewriter
interface TTSCommentary {
  text: string;
  duration_ms: number;
  playing: boolean;
}

function App() {
  const [gameState, setGameState] =
    useState<PokemonGameState>(INITIAL_GAME_STATE);
  const [wsConnected, setWsConnected] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [memoryWrite, setMemoryWrite] = useState<string | null>(null);
  const [ttsCommentary, setTtsCommentary] = useState<TTSCommentary | null>(null);
  const [, setWs] = useState<WebSocket | null>(null);
  
  // Track if we have established an initial connection to detect reconnections
  const initialConnectionMade = useRef(false);

  useEffect(() => {
    let websocket: WebSocket | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    const connectWebSocket = () => {
      websocket = new WebSocket("ws://localhost:8765");
      setWs(websocket);

      websocket.onopen = () => {
        console.log("WS Connected");
        setWsConnected(true);
        
        if (initialConnectionMade.current) {
          // If we've connected before and are reconnecting, reload the page
          // to ensure a clean state from the fresh backend process.
          window.location.reload();
        } else {
          initialConnectionMade.current = true;
        }
      };

      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleGameUpdate(data);
        } catch {
          // Silently ignore malformed messages
        }
      };

      websocket.onclose = () => {
        console.log("WS Closed - attempting reconnect in 3s...");
        setWsConnected(false);
        // Try to reconnect
        reconnectTimeout = setTimeout(connectWebSocket, 3000);
      };

      websocket.onerror = (err) => {
        console.error("WS Error:", err);
        websocket?.close();
      };
    };

    connectWebSocket();

    return () => {
      if (websocket) {
        // Remove listener to prevent auto-reconnect loop on unmount
        websocket.onclose = null; 
        websocket.close();
      }
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  // Handle Pokemon-specific WebSocket messages from existing Vue backend
  const handleGameUpdate = (data: any) => {
    if (!data || typeof data !== "object") return;

    // Handle direct state updates (from Vue app backend)
    if (
      data.actions !== undefined ||
      data.badges !== undefined ||
      data.currentTeam !== undefined ||
      data.currentCycleTime !== undefined ||
      data.prevCycleTime !== undefined ||
      data.avgCycleTime !== undefined ||
      data.cycleTiming !== undefined
    ) {
      setGameState((prev) => {
        const newState = { ...prev };

        // Update all direct state properties
        Object.keys(data).forEach((key) => {
          if (
            key === "log_entry" ||
            key === "vision_log" ||
            key === "response_log"
          ) {
            // Handle these separately
            return;
          }

          if (key === "goals" && data.goals) {
            // Transform goals to ensure consistent structure
            newState.goals = {
              primary: data.goals.primary || prev.goals.primary,
              secondary: data.goals.secondary || prev.goals.secondary,
              tertiary: data.goals.tertiary || prev.goals.tertiary,
            };
          } else if (key === "currentTeam" && Array.isArray(data.currentTeam)) {
            // Transform team data to Pokemon interface
            newState.currentTeam = data.currentTeam.map(
              (p: any) =>
                ({
                  id: p.name || "unknown",
                  name: p.name || "Unknown",
                  nickname: p.nickname,
                  level: p.level || 0,
                  type: p.type || "Normal",
                  hp: p.hp || 0,
                  maxHp: p.maxHp || 0,
                  isFainted: p.hp <= 0,
                  location: "party",
                }) as Pokemon,
            );
          } else {
            (newState as any)[key] = data[key];
          }
        });

        return newState;
      });
    }

    // Handle full state history (initial load or reconnect)
    if (data.log_history && Array.isArray(data.log_history)) {
       const historyLogs = data.log_history.map((log: any) => ({
         id: log.id || `hist-${Date.now()}-${Math.random()}`,
         timestamp: log.timestamp ? new Date(log.timestamp).toISOString() : new Date().toISOString(),
         text: log.text,
         is_action: log.is_action,
         is_vision: log.is_vision,
         is_response: log.is_response,
         type: log.is_vision ? "vision" : log.is_response ? "response" : "action",
         screenshot_base64: log.screenshot_base64, // Preserve if present
       }));
       
       // Inject latest screenshot into first vision log if missing
       // This handles reconnect where DB logs don't have screenshot data
       if (data.latest_screenshot_base64) {
         for (let i = 0; i < historyLogs.length; i++) {
           if (historyLogs[i].is_vision && !historyLogs[i].screenshot_base64) {
             historyLogs[i].screenshot_base64 = data.latest_screenshot_base64;
             break; // Only inject into first (most recent) vision log
           }
         }
       }
       
       // Replace logs entirely on initial history load to avoid dupes
       setLogs(historyLogs);
    }

    // Handle log entries
    if (data.log_entry && data.log_entry.text) {
      const newLog: LogEntry = {
        id: data.log_entry.id || `log-${Date.now()}`,
        timestamp: new Date().toISOString(),
        text: data.log_entry.text,
        is_action: data.log_entry.is_action || false,
        type: "action",
      };
      setLogs((prev) => [newLog, ...prev].slice(0, 3000)); // Match Vue app limit
    }

    // Handle vision analysis logs
    if (data.vision_log && data.vision_log.text) {
      const newLog: LogEntry = {
        id: data.vision_log.id || `vision-${Date.now()}`,
        timestamp: data.vision_log.timestamp
          ? new Date(data.vision_log.timestamp).toISOString() // Convert ms timestamp to ISO string
          : new Date().toISOString(), // Fallback to current time
        text: data.vision_log.text,
        is_vision: true,
        type: "vision",
        screenshot_base64: data.vision_log.screenshot_base64, // CRITICAL: Pass image data to UI
      };
      setLogs((prev) => [newLog, ...prev].slice(0, 3000));
    }

    // Handle response logs
    if (data.response_log && data.response_log.text) {
      const newLog: LogEntry = {
        id: data.response_log.id || `response-${Date.now()}`,
        timestamp: new Date().toISOString(),
        text: data.response_log.text,
        is_response: true,
        type: "response",
      };
      setLogs((prev) => [newLog, ...prev].slice(0, 3000));
    }

    // Handle memory writes - Fixed to ensure UI updates
    if (data.memory_write && data.memory_write.text) {
      setMemoryWrite(data.memory_write.text);
    }

    // Handle TTS commentary (for synchronized typewriter animation)
    if (data.tts_commentary) {
      console.log("TTS Commentary received:", data.tts_commentary);
      setTtsCommentary(data.tts_commentary);
    }

    // Handle action_execute (triggers button animation at correct time)
    if (data.action_execute) {
      console.log("Action execute received - triggering animation");
      setGameState((prev) => ({
        ...prev,
        animateActions: Date.now(), // Use timestamp to trigger re-render
      }));
    }

    // Handle bulk logs
    if (data.logs && Array.isArray(data.logs)) {
      const newLogs = data.logs.map((log: any) => ({
        id: log.id || `log-${Date.now()}-${Math.random()}`,
        timestamp: new Date().toISOString(),
        text: log.text || log.message,
        is_action: log.is_action,
        is_vision: log.is_vision,
        is_response: log.is_response,
        type: "info",
      }));
      setLogs((prev) => [...newLogs, ...prev].slice(0, 3000));
    }
  };



  return (
    <PokemonStreamOverlay
      gameState={gameState}
      wsConnected={wsConnected}
      logs={logs}
      memoryWrite={memoryWrite}
      onMemoryWriteClear={() => setMemoryWrite(null)}
      ttsCommentary={ttsCommentary}
      onTtsCommentaryComplete={() => setTtsCommentary(null)}
    />
  );
}

export default App;
