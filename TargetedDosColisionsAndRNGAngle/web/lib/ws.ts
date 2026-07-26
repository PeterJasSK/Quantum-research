// Tier B live data source (AC-5, OQ-2). Browser WS client -- in scope per
// plan; the controller-side push server is P6 Tier B, not implemented yet
// (see plan §Dependencies P4, §Out of scope). Kept as a typed stub so
// lib/datasource.ts's createLiveDataSource() has a real client to wire up
// once the Ryu controller exposes a port-stat WS endpoint.
export interface PortStatsMessage {
  link_utils: number[]; // link{i}_util, matches testbed/metrics/csv_writer.py columns
  victim_mbps: number;
  jains_index: number;
}

export function connectPortStatsSocket(
  url: string,
  onMessage: (message: PortStatsMessage) => void,
): () => void {
  const socket = new WebSocket(url);
  socket.onmessage = (event: MessageEvent<string>) => {
    onMessage(JSON.parse(event.data) as PortStatsMessage);
  };
  return () => socket.close();
}
