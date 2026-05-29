import { test } from "node:test";
import assert from "node:assert/strict";
import { Queue, QueueContractError, type Validator } from "./queue";

interface Task {
  id: string;
  payload: string;
}

const isTask: Validator<Task> = (v): v is Task =>
  typeof v === "object" &&
  v !== null &&
  typeof (v as Task).id === "string" &&
  typeof (v as Task).payload === "string";

test("queue preserves FIFO ordering", async () => {
  const q = new Queue<Task>(isTask, "tasks");
  q.enqueue({ id: "1", payload: "a" });
  q.enqueue({ id: "2", payload: "b" });
  q.enqueue({ id: "3", payload: "c" });

  assert.equal(q.size, 3);
  assert.equal((await q.dequeue()).id, "1");
  assert.equal((await q.dequeue()).id, "2");
  assert.equal((await q.dequeue()).id, "3");
  assert.equal(q.size, 0);
});

test("enqueue rejects a schema-violating message with a typed error", () => {
  const q = new Queue<Task>(isTask, "tasks");
  assert.throws(
    () => q.enqueue({ id: 5, payload: "missing-string-id" }),
    (err: unknown) => {
      assert.ok(err instanceof QueueContractError, "expected QueueContractError");
      assert.match((err as QueueContractError).message, /does not satisfy/);
      return true;
    }
  );
  // The rejected message must NOT be stored.
  assert.equal(q.size, 0);
});

test("dequeue on an empty queue rejects", async () => {
  const q = new Queue<Task>(isTask);
  await assert.rejects(() => q.dequeue(), /empty/);
});

test("constructor requires a validator function", () => {
  // @ts-expect-error intentionally passing a non-function validator
  assert.throws(() => new Queue<Task>(null), TypeError);
});
