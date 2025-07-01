export class LRUCache<K, V> {
  private capacity: number;
  private cache = new Map<K, V>();
  private keyOrder: K[] = [];

  constructor(capacity: number) {
    this.capacity = capacity;
  }

  get(key: K): V | undefined {
    const value = this.cache.get(key);
    if (value !== undefined) {
      // Move key to the end (most recently used)
      this.keyOrder = this.keyOrder.filter(k => k !== key);
      this.keyOrder.push(key);
    }
    return value;
  }

  set(key: K, value: V): void {
    if (this.cache.size >= this.capacity && !this.cache.has(key)) {
      // Evict least recently used item
      const lruKey = this.keyOrder.shift();
      if (lruKey !== undefined) {
        this.cache.delete(lruKey);
      }
    }

    this.cache.set(key, value);
    // Update key order
    this.keyOrder = this.keyOrder.filter(k => k !== key);
    this.keyOrder.push(key);
  }

  keys(): IterableIterator<K> {
    return this.cache.keys();
  }

  values(): IterableIterator<V> {
    return this.cache.values();
  }

  entries(): IterableIterator<[K, V]> {
    return this.cache.entries();
  }

  size(): number {
    return this.cache.size;
  }

  clear(): void {
    this.cache.clear();
    this.keyOrder = [];
  }
}
