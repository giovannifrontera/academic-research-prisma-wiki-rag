import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { execFile, spawn } from "node:child_process";
import { promisify } from "node:util";
import { existsSync, writeFileSync, appendFileSync } from "node:fs";
import { join, dirname } from "node:path";

const execFileAsync = promisify(execFile);

export default definePluginEntry({
  id: "wiki-context-plugin",
  name: "Wiki Context Injector",
  description:
    "Runs wiki_context.py before every prompt and prepends relevant wiki pages as <wiki-context> block. " +
    "On the first prompt of each session, also prepends a <wiki-briefing> with session state and mandatory rules.",

  register(api) {
    // OpenClaw passes plugin-specific config via api.pluginConfig, not api.config
    const cfg = ((api as Record<string, unknown>).pluginConfig ?? {}) as {
      workspace?: string;
      wikiContextScript?: string;
      pythonExecutable?: string;
      k?: number;
      maxChars?: number;
      timeoutMs?: number;
      debug?: boolean;
    };

    const debug = cfg.debug === true;

    if (!cfg.workspace || !cfg.wikiContextScript) {
      console.warn(
        "[wiki-context-plugin] Missing required config: workspace and wikiContextScript must be set."
      );
      return;
    }

    const workspace = cfg.workspace;
    const wikiContextScript = cfg.wikiContextScript;

    if (!existsSync(wikiContextScript)) {
      console.warn(
        `[wiki-context-plugin] wiki_context.py not found at: ${wikiContextScript}`
      );
      return;
    }

    const python = cfg.pythonExecutable ?? "python";
    const k = String(cfg.k ?? 3);
    const maxChars = String(cfg.maxChars ?? 600);
    const timeoutMs = cfg.timeoutMs ?? 15_000;
    const serverPort = (cfg as Record<string, unknown>).serverPort ?? 7331;
    const debugLog = `${workspace}/.wiki-plugin-debug.log`;

    // wiki_check_setup.py lives next to wiki_context.py in scripts/
    const checkSetupScript = join(dirname(wikiContextScript), "wiki_check_setup.py");

    // Emitted once per plugin lifetime (= once per session).
    // Gives the agent a <wiki-briefing> with session state and mandatory rules
    // before it processes any user message.
    let sessionBriefingSent = false;

    // Startup: verify python can import lancedb (fail silently, warn loudly)
    void (async () => {
      try {
        await execFileAsync(python, ["-c", "import lancedb"], { timeout: 10_000 });
      } catch {
        const msg =
          `[wiki-context-plugin] WARNING: '${python}' cannot import lancedb.\n` +
          `Wiki context will not be injected. Set 'pythonExecutable' to the absolute path.\n` +
          `Find the correct path: ${python} -c "import sys; print(sys.executable)"`;
        console.warn(msg);
        if (debug) {
          try {
            writeFileSync(debugLog, `[${new Date().toISOString()}] STARTUP FAIL\n${msg}\n`, "utf-8");
          } catch {}
        }
      }
    })();

    // Startup: ensure the wiki server is running — restart it if not.
    // Uses detached + unref so the server survives OpenClaw gateway restarts;
    // the probe prevents spawning a duplicate if it is already up.
    void (async () => {
      try {
        await fetch(`http://localhost:${serverPort}/`, { signal: AbortSignal.timeout(1_500) });
        // Any HTTP response means the server is already up — nothing to do.
      } catch {
        // Connection refused — server is down, spawn it.
        const wikiPy = join(dirname(wikiContextScript), "wiki.py");
        const child = spawn(
          python,
          [wikiPy, "serve", "--workspace", workspace, "--port", String(serverPort)],
          { detached: true, stdio: "ignore" }
        );
        child.unref(); // let the server outlive this plugin process
        if (debug) {
          try {
            appendFileSync(debugLog,
              `[${new Date().toISOString()}] wiki server spawned (PID ${child.pid})\n`, "utf-8");
          } catch {}
        }
      }
    })();

    api.on(
      "before_prompt_build",
      async (event) => {
        const ev = event as Record<string, unknown>;
        const eventKeys = Object.keys(ev).join(", ");

        // Try known field names across SDK versions.
        const userText: string =
          ev.userMessage as string ??
          ev.prompt as string ??
          ev.currentPrompt as string ??
          ev.input as string ??
          ev.message as string ??
          ev.text as string ??
          "";

        if (!userText.trim()) {
          if (debug) {
            try {
              appendFileSync(debugLog,
                `[${new Date().toISOString()}] hook fired but userText empty\nevent keys: ${eventKeys}\n`, "utf-8");
            } catch {}
          }
          return {};
        }

        const parts: string[] = [];

        // --- Session briefing (first prompt only) ---
        // Inject the session briefing on the very first before_prompt_build call.
        if (!sessionBriefingSent) {
          sessionBriefingSent = true;
          if (existsSync(checkSetupScript)) {
            try {
              const { stdout } = await execFileAsync(
                python,
                [checkSetupScript, "--workspace", workspace],
                { encoding: "utf-8", timeout: 15_000 }
              );
              const briefing = stdout.trim();
              if (briefing) parts.push(briefing);
            } catch {
              // Fail silently — never block the user's prompt.
            }
          }
        }

        // --- Wiki context (every prompt) ---
        // Fast path: ask the already-running server (model stays in memory → ~50ms).
        // Slow path fallback: subprocess (cold-starts the model every call → 2-5s).
        let contextInjected = false;
        try {
          const url = `http://localhost:${serverPort}/api/context?q=${encodeURIComponent(userText)}&k=${k}&max_chars=${maxChars}`;
          const resp = await fetch(url, { signal: AbortSignal.timeout(3_000) });
          if (resp.ok) {
            const text = (await resp.text()).trim();
            if (text) {
              parts.push(text);
              contextInjected = true;
            }
          }
        } catch {
          // Server not reachable — fall through to subprocess.
        }

        if (!contextInjected) {
          try {
            const result = await execFileAsync(
              python,
              [
                wikiContextScript,
                "--workspace", workspace,
                "--q", userText,
                "--k", k,
                "--max-chars", maxChars,
              ],
              { encoding: "utf-8", timeout: timeoutMs }
            );
            const context = result.stdout.trim();
            if (context) parts.push(context);
          } catch (err) {
            if (debug) {
              try {
                appendFileSync(debugLog,
                  `[${new Date().toISOString()}] wiki_context.py error: ${String(err)}\n`, "utf-8");
              } catch {}
            }
            // Always fail silently — never block the user's prompt.
          }
        }

        if (debug) {
          try {
            appendFileSync(debugLog,
              `[${new Date().toISOString()}]\n` +
              `event keys: ${eventKeys}\n` +
              `userText (${userText.length} chars): ${userText.slice(0, 120)}\n` +
              `output (${parts.join("\n").length} chars): ${parts.join("\n").slice(0, 200)}\n`, "utf-8");
          } catch {}
        }

        const output = parts.join("\n\n").trim();
        if (output) {
          return { prependContext: output };
        }

        return {};
      },
      { priority: 50, timeoutMs: timeoutMs + 5_000 }
    );

    // Tool: wiki_process_raw — promote raw/ files to the index
    // Exposed so OpenClaw agents can trigger it from chat
    if (typeof (api as Record<string, unknown>).registerTool === "function") {
      try {
        (api as unknown as Record<string, (...args: unknown[]) => unknown>).registerTool(
          "wiki_process_raw",
          async (params: { project?: string }) => {
            const wikiPy = join(dirname(wikiContextScript), "wiki.py");
            const args = ["process-raw", "--workspace", workspace];
            if (params?.project) {
              args.push("--project", params.project);
            }
            try {
              const { stdout } = await execFileAsync(python, [wikiPy, ...args], {
                encoding: "utf-8",
                timeout: 120_000,
              });
              return JSON.parse(stdout);
            } catch (err) {
              return { status: "error", message: String(err) };
            }
          }
        );
      } catch (e) {
        console.warn("[wiki-context-plugin] registerTool failed:", e);
      }
    }
  },
});
