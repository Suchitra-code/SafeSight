import { getRunEvents } from './api.js';
import { setNodeActive, setNodeCompleted, resetPipelineViz } from './pipeline_viz.js';

export async function replayRun(runId) {
  if (!runId) return;

  try {
    const data = await getRunEvents(runId);
    const events = data.events || [];
    if (events.length === 0) return;

    resetPipelineViz();

    for (const ev of events) {
      if (ev.event_type === 'node_started') {
        setNodeActive(ev.node_name);
      } else if (ev.event_type === 'node_finished') {
        setNodeCompleted(ev.node_name);
      }
      // Replay pacing delay
      await new Promise(r => setTimeout(r, 200));
    }
  } catch (err) {
    console.error('Failed to replay run:', err);
  }
}
