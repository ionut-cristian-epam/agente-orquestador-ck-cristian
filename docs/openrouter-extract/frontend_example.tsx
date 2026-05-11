/**
 * Minimal CopilotKit frontend that consumes AG-UI events.
 * Drop into any Next.js app.
 *
 * Requirements:
 *   npm install @copilotkit/react-core @copilotkit/react-ui @ag-ui/client
 */
import { HttpAgent } from "@ag-ui/client";
import {
  CopilotKitProvider,
  CopilotChat,
} from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

const BACKEND = "http://localhost:8000";

// 1. Create HttpAgent pointing to your AG-UI endpoint
const agent = new HttpAgent({
  url: `${BACKEND}/agent/my_agent`,
});

// 2. Wrap in CopilotKitProvider + CopilotChat
export default function ChatPage() {
  return (
    <CopilotKitProvider agents__unsafe_dev_only={[agent]}>
      {/* CopilotChat automatically renders:
          - Text messages (TextMessageChunkEvent)
          - Thinking boxes (ReasoningMessageStart/Content/End)
          - Tool calls (ToolCallChunk → auto-wrapped with Start/Args/End)
          - Tool results (ToolCallResultEvent)

          Zero custom rendering code needed. */}
      <CopilotChat
        className="h-screen"
        labels={{
          title: "Agent Chat",
          placeholder: "Ask something...",
        }}
      />
    </CopilotKitProvider>
  );
}
