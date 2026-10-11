import { describe, expect, it } from 'vitest';

describe('api client', () => {
  it('exports listTasks', async () => {
    const { api } = await import('./client');
    expect(typeof api.listTasks).toBe('function');
    expect(typeof api.createTask).toBe('function');
    expect(typeof api.respondDecision).toBe('function');
  });
});
