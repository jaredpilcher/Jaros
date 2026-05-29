import {
  grant,
  revoke,
  type Grants,
  type GrantSpec,
  type RevocableGrants,
} from "./capabilities";
import { ruleFor, describeRules, type Rule } from "./rules";

// #EXT-005-REQ-1 Start
// #EXT-005-REQ-2 Start
/**
 * The architectural harness — the unyielding mediator every agent runs inside.
 *
 * Agents hold no ambient power. They are spawned with only a {@link Grants}
 * bundle (no global queue/fs/network references) and reach the world solely by
 * calling {@link Harness.request}. Each request is validated against the active
 * rule set (`./rules`) *before* any effect, and performed only through the
 * agent's granted handles.
 *
 * The harness fails closed: an unknown action, an action with no rule, or an
 * action the agent lacks the capability for is refused and reported with no
 * side effect (default-deny). The rule set lives in code/config and is not
 * reachable for mutation by agent code.
 */

/** An action an agent asks the harness to perform on its behalf. */
export interface Action {
  /** Canonical action type; matched against the rule set. */
  readonly type: string;
  /** Action-specific arguments (e.g. message to send, path + data to write). */
  readonly args?: Record<string, unknown>;
}

/** Outcome of a {@link Harness.request}: either an allowed result or a denial. */
export type RequestResult =
  | { readonly ok: true; readonly value: unknown }
  | { readonly ok: false; readonly reason: string };

/** A single recorded mediation event, for audit/reporting of denials. */
export interface AuditEntry {
  readonly agentId: string;
  readonly action: string;
  readonly allowed: boolean;
  readonly reason?: string;
}

/** A spawned agent's view of the harness: its id and its granted handles. */
export interface AgentContext {
  readonly agentId: string;
  /** ONLY the granted handles — no global queue/fs/network references. */
  readonly grants: Grants;
}

/** Internal registration record kept by the harness per agent. */
interface Registration {
  readonly revocable: RevocableGrants;
}

export class Harness {
  private readonly agents = new Map<string, Registration>();
  private readonly auditLog: AuditEntry[] = [];

  /**
   * Register/spawn an agent, minting its capabilities from `spec`. The returned
   * {@link AgentContext} carries the agent's id and ONLY its granted handles —
   * the harness passes no global queue/fs/network references. The revocation
   * function is retained privately by the harness, not handed to the agent.
   */
  spawn(agentId: string, spec: GrantSpec): AgentContext {
    if (typeof agentId !== "string" || agentId.length === 0) {
      throw new TypeError("spawn requires a non-empty agentId.");
    }
    if (this.agents.has(agentId)) {
      throw new Error(`Agent "${agentId}" is already registered.`);
    }
    const revocable = grant(spec);
    this.agents.set(agentId, { revocable });
    return { agentId, grants: revocable.grants };
  }

  /**
   * Tear down an agent, revoking every capability it was granted. After this,
   * any handle the agent still holds fails closed, and further requests from
   * that agent are denied (it is no longer registered).
   */
  teardown(agentId: string): void {
    const reg = this.agents.get(agentId);
    if (!reg) {
      return;
    }
    revoke(reg.revocable);
    this.agents.delete(agentId);
  }

  /**
   * Mediate one agent action. Validates `action` against the active rules and,
   * if allowed, performs it via the agent's granted handle. Default-deny: an
   * unregistered agent, unknown/disallowed action, or missing capability is
   * refused and recorded in the audit log with NO side effect.
   */
  async request(agentId: string, action: Action): Promise<RequestResult> {
    const deny = (reason: string): RequestResult => {
      this.auditLog.push({ agentId, action: action?.type ?? "<none>", allowed: false, reason });
      return { ok: false, reason };
    };

    const reg = this.agents.get(agentId);
    if (!reg) {
      return deny(`Unknown agent "${agentId}".`);
    }
    if (!action || typeof action.type !== "string") {
      return deny("Malformed action: missing action type.");
    }

    const rule: Rule | undefined = ruleFor(action.type);
    if (!rule) {
      return deny(`No rule permits action "${action.type}" (default-deny).`);
    }

    const grants = reg.revocable.grants;
    const args = action.args ?? {};

    // Perform ONLY via the granted handle matching the rule's required
    // capability. A missing handle is a default-deny denial — no side effect.
    switch (rule.requires) {
      case "QueueSend": {
        if (!grants.queueSend) {
          return deny(`Agent "${agentId}" lacks capability QueueSend.`);
        }
        grants.queueSend.send(args.message);
        break;
      }
      case "QueueReceive": {
        if (!grants.queueReceive) {
          return deny(`Agent "${agentId}" lacks capability QueueReceive.`);
        }
        const value = await grants.queueReceive.receive();
        this.auditLog.push({ agentId, action: action.type, allowed: true });
        return { ok: true, value };
      }
      case "FsWrite": {
        if (!grants.fsWrite) {
          return deny(`Agent "${agentId}" lacks capability FsWrite.`);
        }
        grants.fsWrite.write(String(args.path), String(args.data ?? ""));
        break;
      }
      case "FsRead": {
        if (!grants.fsRead) {
          return deny(`Agent "${agentId}" lacks capability FsRead.`);
        }
        const value = grants.fsRead.read(String(args.path));
        this.auditLog.push({ agentId, action: action.type, allowed: true });
        return { ok: true, value };
      }
      default:
        return deny(`Unsupported capability requirement (default-deny).`);
    }

    this.auditLog.push({ agentId, action: action.type, allowed: true });
    return { ok: true, value: undefined };
  }

  /** Read-only snapshot of the mediation audit log (allowed + denied events). */
  audit(): readonly AuditEntry[] {
    return this.auditLog.map((e) => ({ ...e }));
  }

  /** Introspect the active architectural rule set (delegates to `./rules`). */
  describeRules(): readonly Rule[] {
    return describeRules();
  }
}
// #EXT-005-REQ-2 End
// #EXT-005-REQ-1 End
