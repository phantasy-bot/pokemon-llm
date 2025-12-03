import React, { useEffect, useRef } from "react";
import type { LogEntry } from "../types/gameTypes";

interface ActionLogProps {
  logs: LogEntry[];
}

const ActionLog: React.FC<ActionLogProps> = ({ logs }) => {
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll to latest log entry
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getLogClassName = (type: string) => {
    switch (type) {
      case "action":
        return "log-action";
      case "battle":
        return "log-battle";
      case "system":
        return "log-system";
      case "error":
        return "log-error";
      case "ai":
        return "log-ai";
      default:
        return "";
    }
  };

  return (
    <div className="action-log">
      <h2>Action Log</h2>
      <div className="log-container">
        {logs.length === 0 ? (
          <div className="no-logs">
            <p>Waiting for actions...</p>
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id ?? String(log.timestamp)}
              className={`log-entry ${getLogClassName(log.type)}`}
            >
              <span className="log-time">
                {new Date(log.timestamp || new Date()).toLocaleTimeString(
                  "en-US",
                  {
                    hour12: false,
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  },
                )}
              </span>
              <span className="log-message">{log.message}</span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};

export default ActionLog;
