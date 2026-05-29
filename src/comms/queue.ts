// #EXT-006-REQ-1 Start
/**
 * Rigid, typed queue abstraction — one of the only two sanctioned inter-agent
 * channels (the other being the shared file system, see `./fs`).
 *
 * Agents never address each other directly: a producer `enqueue`s a message and
 * a consumer `dequeue`s it. Every message crosses a schema gate at enqueue time
 * so a contract violation fails loudly with a typed error *before* the message
 * is ever stored or made visible to a consumer.
 *
 * Delivery semantics (explicit, see [REQ-1]):
 *   - Ordering:   in-memory FIFO. Messages are dequeued in the exact order they
 *                 were accepted by `enqueue`.
 *   - Delivery:   at-least-once. A `dequeue` resolves with the next message and
 *                 removes it from the queue. There is no acknowledgement step,
 *                 so a consumer that crashes after `dequeue` but before acting
 *                 simply loses that delivery attempt; producers/consumers must
 *                 tolerate a message being processed one-or-more times. This is
 *                 deliberately NOT exactly-once.
 *   - Durability: in-memory only. The queue does not survive process restart;
 *                 durable exchange is the file system's job (`./fs`).
 *
 * The queue stores no callbacks/handles and exposes no path for a producer to
 * reach a consumer except through the message data itself.
 */

/**
 * A `Validator<T>` decides whether an arbitrary value satisfies a message
 * contract. It is a TypeScript type guard so a successful validation also
 * narrows the value to `T` for the caller.
 *
 * Implementations MUST be pure and MUST throw nothing — they return `false` for
 * any value that violates the contract. The queue turns a `false` result into a
 * {@link QueueContractError}.
 */
export type Validator<T> = (value: unknown) => value is T;

/**
 * Typed error raised when a message fails its contract validation at enqueue
 * time. Contract/layout violations across the comms fabric fail loudly with a
 * typed error ([REQ-4]); this is the queue side of that guarantee.
 */
export class QueueContractError extends Error {
  /** The value that violated the contract (kept for diagnostics). */
  readonly value: unknown;

  constructor(message: string, value: unknown) {
    super(message);
    this.name = "QueueContractError";
    this.value = value;
    // Restore prototype chain for `instanceof` across the CommonJS/ES boundary.
    Object.setPrototypeOf(this, QueueContractError.prototype);
  }
}

/**
 * Generic FIFO queue over a rigid, typed message contract `T`.
 *
 * Construct with a {@link Validator} that defines the contract. Each
 * `enqueue` validates against it and rejects violations with a
 * {@link QueueContractError} before storage.
 */
export class Queue<T> {
  private readonly items: T[] = [];
  private readonly validate: Validator<T>;
  private readonly name: string;

  /**
   * @param validator type guard defining the message contract.
   * @param name      optional queue name used in error messages.
   */
  constructor(validator: Validator<T>, name = "queue") {
    if (typeof validator !== "function") {
      throw new TypeError("Queue requires a validator function.");
    }
    this.validate = validator;
    this.name = name;
  }

  /** Number of messages currently buffered. */
  get size(): number {
    return this.items.length;
  }

  /**
   * Validate `msg` against the contract and, if it passes, append it to the
   * tail of the queue. Throws {@link QueueContractError} on a contract
   * violation; the message is NOT stored in that case.
   */
  enqueue(msg: unknown): void {
    if (!this.validate(msg)) {
      throw new QueueContractError(
        `Message rejected by ${this.name}: does not satisfy the message contract.`,
        msg
      );
    }
    // `validate` narrowed `msg` to `T`.
    this.items.push(msg);
  }

  /**
   * Remove and return the message at the head of the queue (FIFO). Rejects if
   * the queue is empty. At-least-once delivery: the message is removed as it is
   * handed to the caller; there is no acknowledgement.
   */
  async dequeue(): Promise<T> {
    if (this.items.length === 0) {
      throw new Error(`Cannot dequeue from empty ${this.name}.`);
    }
    return this.items.shift() as T;
  }

  /** Non-removing peek at the head message, or `undefined` when empty. */
  peek(): T | undefined {
    return this.items[0];
  }
}
// #EXT-006-REQ-1 End
