# Architecture

## Overview

The current implementation is intentionally compact.

```text
claude_node/
├── __init__.py
├── controller.py
└── router.py
```

This small code surface is a strength. It makes the system easier to inspect and reason about.

## Current modules

## `controller.py`

This module currently contains the two most important objects in the project:

- `ClaudeMessage`
- `ClaudeController`

### `ClaudeMessage`
`ClaudeMessage` is the parsed representation of one JSON line emitted by Claude Code.

Its job is deliberately small:

- identify message type,
- expose helpers for common message patterns,
- and extract useful content from assistant and tool-result messages.

It should remain a lightweight value object rather than becoming an active controller abstraction.

### `ClaudeController`
`ClaudeController` is the core runtime object.

It is responsible for:

- building the `claude` command,
- launching the subprocess,
- reading stdout and stderr,
- writing user messages to stdin,
- waiting for turn completion,
- tracking the session id,
- and exposing minimal convenience methods around the message stream.

This object should stay centered on **one subprocess = one session**.

## `router.py`

This module contains:

- `AgentNode`
- `MultiAgentRouter`

### `AgentNode`
A simple node configuration wrapper that stores controller options and starts the controller when requested.

### `MultiAgentRouter`
A thin multi-session coordination layer.

Current responsibilities include:

- storing named nodes,
- starting and stopping them,
- sending to one node,
- wrapping and routing text to another node,
- and performing parallel fan-out.

The router should remain a primitive layer rather than becoming a semantics-heavy orchestration system.

## Current design boundaries

The current repository already suggests a healthy architecture boundary:

### Layer 1: Message parsing
Represent one CLI event cleanly.

### Layer 2: Session control
Control one subprocess and synchronize turn boundaries.

### Layer 3: Lightweight routing
Coordinate multiple independent sessions when needed.

That is enough for this repository.

## Recommended future module boundaries

As the project matures, it would be reasonable to split the code into more modules, for example:

- `messages.py`
- `runtime.py`
- `exceptions.py`
- `transcript.py`

But this should happen only when it improves clarity, not because the project needs to “look bigger”.

## Important architectural rule

The library should preserve this principle:

> every new abstraction must justify itself by making the bridge more reliable or more understandable.

If a feature primarily adds product surface area instead of bridge quality, it probably does not belong here.
