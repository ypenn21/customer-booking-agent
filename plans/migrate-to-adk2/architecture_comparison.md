# Architecture Comparison: ADK 1.x vs ADK 2.0

This document visualizes the structural changes during the migration to ADK 2.0 Workflows.

## ADK 1.x: Hierarchical Delegation (Current)

In the current setup, the `Customers` agent acts as a "manager" that uses a custom tool to talk to the `Bookings` agent. This creates a nested reasoning loop.

```mermaid
sequenceDiagram
    participant User
    participant CustomersAgent
    participant BookingsTool
    participant BookingsAgent
    
    User->>CustomersAgent: "Book a meeting for Alice"
    CustomersAgent->>CustomersAgent: Reason: "I need Alice's ID"
    CustomersAgent->>CustomersAgent: Tool Call: get_customer("Alice")
    CustomersAgent->>BookingsTool: Tool Call: bookings("Book meeting for u1022")
    BookingsTool->>BookingsAgent: Remote stream_query(...)
    BookingsAgent->>BookingsAgent: Reason: "I need to call Graph API"
    BookingsAgent->>BookingsAgent: Tool Call: create_calendar_invite(...)
    BookingsAgent-->>BookingsTool: Response: "Meeting booked"
    BookingsTool-->>CustomersAgent: Response: "Meeting booked"
    CustomersAgent-->>User: "I've booked your meeting for Alice."
```

## ADK 2.0: Graph-based Workflow (Proposed)

In ADK 2.0, the "management" is handled by the graph structure. Routing is explicit, and deterministic tasks are handled by function nodes, saving LLM time.

```mermaid
graph TD
    Start((Start)) --> Auth[Auth Gate fn]
    Auth --> Router{Router Node}
    
    Router -- "Booking" --> PreBooking[User ID Resolution fn]
    PreBooking --> BookingNode[Bookings LLM Node]
    
    Router -- "Lookup" --> CustomerNode[Customers LLM Node]
    
    BookingNode -- "Success" --> End((End))
    CustomerNode -- "Done" --> End
```

### Key Differences

| Feature | ADK 1.x | ADK 2.0 |
|---------|---------|---------|
| **Orchestration** | Implicit (via tools/callbacks) | Explicit (via Graph edges) |
| **Delegation** | Heavy (Remote SDK calls) | Lightweight (Node transitions) |
| **State** | Hidden / Local | Shared `State` object |
| **Logic** | Mostly LLM-driven | Mixed (Function + LLM nodes) |
| **Debugging** | Hard (nested traces) | Easy (Visual graph flow) |
| **Latency** | High (multiple LLM calls) | Low (deterministic pre-processing) |
