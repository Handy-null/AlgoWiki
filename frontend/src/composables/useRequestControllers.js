import { onBeforeUnmount } from "vue";

export function useRequestControllers() {
  const controllers = new Map();

  function normalizeKey(key) {
    return String(key || "default");
  }

  function replace(key) {
    const normalizedKey = normalizeKey(key);
    cancel(normalizedKey);
    const controller = new AbortController();
    controllers.set(normalizedKey, controller);
    return controller;
  }

  function cancel(key) {
    const normalizedKey = normalizeKey(key);
    const controller = controllers.get(normalizedKey);
    if (!controller) return;
    controller.abort();
    controllers.delete(normalizedKey);
  }

  function isCurrent(key, controller) {
    return controllers.get(normalizeKey(key)) === controller;
  }

  function release(key, controller) {
    const normalizedKey = normalizeKey(key);
    if (controllers.get(normalizedKey) !== controller) return false;
    controllers.delete(normalizedKey);
    return true;
  }

  function cancelAll() {
    for (const controller of controllers.values()) {
      controller.abort();
    }
    controllers.clear();
  }

  onBeforeUnmount(() => {
    cancelAll();
  });

  return {
    replace,
    cancel,
    isCurrent,
    release,
    cancelAll,
  };
}
