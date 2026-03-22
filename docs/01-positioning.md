# Positioning

## Core identity

`claude-node` is a **subprocess-based Python bridge for persistent Claude Code sessions**.

That identity is narrow on purpose.

The project is strongest when it stays focused on one layer:

- launching and controlling a local `claude` process,
- sending and receiving `stream-json` messages,
- tracking sessions,
- exposing a thin Python interface,
- and providing lightweight multi-session routing primitives.

## Why this position matters

There are two easy ways for a project like this to lose focus:

1. it pretends to be a replacement for richer official integrations,
2. or it grows upward into a large workflow / orchestration platform.

This project should do neither.

Its value comes from being:

- thin,
- explicit,
- process-oriented,
- transparent,
- and easy to embed.

## What the project is

The project is best understood as a combination of four roles:

### 1. Python bridge
It lets Python systems control Claude Code through a local CLI subprocess.

### 2. Persistent session controller
It keeps one CLI process alive across turns and tracks the session.

### 3. Runtime integration layer
It helps existing applications integrate Claude Code without absorbing a much larger abstraction surface.

### 4. Protocol reference implementation
It shows how to drive `stream-json` correctly and what to expect from the message stream.

## What the project is not

This repository should not be positioned as:

- an API SDK replacement,
- a general multi-agent platform,
- a workflow engine,
- a memory framework,
- a dashboard product,
- or a full AI organization runtime.

Those can exist elsewhere.

## Main value proposition

The main value proposition should be expressed like this:

> `claude-node` is a thin subprocess-first control layer for developers who want explicit control over persistent Claude Code sessions from Python.

## Secondary value propositions

These are strong secondary messages, but not the main identity:

### Lightweight multi-session routing
The router is useful and interesting, but it should remain a secondary feature rather than the project’s core identity.

### Protocol clarity
The repository can become a trusted reference for `stream-json` behavior, message ordering, and practical pitfalls.

## Packaging vs runtime

This distinction should always be documented clearly:

- the package is pure Python,
- the runtime depends on a local `claude` executable.

That separation is not a weakness. It is part of the design.
